﻿"""
Open Notebook 桌面版主程序入口
用于 PyInstaller 打包为 Windows EXE

启动流程：
1. 启动 SurrealDB 嵌入式实例（从打包资源中释放）
2. 启动 FastAPI 后端（uvicorn）
3. 打开 WebView2 窗口加载前端
4. 关闭窗口时清理 SurrealDB 进程
"""

import os
import sys
import shutil
import socket
import tempfile
import subprocess
import threading
import time
import atexit
import signal
import types
import traceback
from pathlib import Path
from loguru import logger

# === PyInstaller 兼容：处理 tomli 在打包环境下的特殊问题 ===
# tomli 在某些版本会引用 __mypyc 模块，在打包后找不到
# 这里我们使用 tomli_w 替代或提供一个简单的 shim
if hasattr(sys, "_MEIPASS"):
    try:
        import tomli  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        try:
            # 尝试 tomli_w 作为替代
            import tomli_w as tomli  # type: ignore
            sys.modules["tomli"] = tomli
        except ImportError:
            # 提供一个最小的 tomli 兼容 shim（仅支持 loads）
            tomli_shim = types.ModuleType("tomli")
            tomli_shim.__mypyc__ = types.ModuleType("__mypyc")  # 假装存在
            import tomllib
            tomli_shim.loads = tomllib.loads
            tomli_shim.load = tomllib.load
            sys.modules["tomli"] = tomli_shim
            sys.modules["tomli.__mypyc"] = tomli_shim.__mypyc__

    # === PyInstaller 兼容：处理 podcast_creator 依赖链 ===
    # podcast_creator -> moviepy -> imageio 在打包后 metadata 缺失
    # 即使 commands/__init__.py 已做可选导入，仍需在更早阶段阻断真实包加载
    # 通过占位 sys.modules 模块防止任何深层导入触发 imageio 元数据查询
    for _stub_name in (
        "podcast_creator",
        "podcast_creator.core",
        "moviepy",
        "moviepy.audio",
        "moviepy.audio.fx",
        "moviepy.editor",
        "moviepy.video",
        "moviepy.video.fx",
        "imageio",
        "imageio_ffmpeg",
    ):
        if _stub_name not in sys.modules:
            _mod = types.ModuleType(_stub_name)
            _mod.__path__ = []  # 标记为包，阻止 Python 重新扫描
            sys.modules[_stub_name] = _mod

    # 在 moviepy stub 上提供占位类/函数（AudioFileClip/VideoFileClip/CompositeVideoClip
    # 等），使 `from moviepy import X` 在 import 阶段成功；运行时报错但不会阻断
    # PDF/文档等其他功能。这样 open_notebook.graphs.source 等深层模块就能成功导入。
    _mp_stub = sys.modules.get("moviepy")
    if _mp_stub is not None:
        def _mp_unavailable(name):
            def _stub(*args, **kwargs):
                raise ImportError(
                    f"moviepy.{name} is not available in desktop build "
                    "(audio/video editing disabled)"
                )
            return _stub

        for _cls in ("AudioFileClip", "VideoFileClip", "ImageClip",
                     "CompositeVideoClip", "TextClip", "ColorClip",
                     "VideoClip", "AudioClip", "ImageSequenceClip"):
            if not hasattr(_mp_stub, _cls):
                setattr(_mp_stub, _cls, _mp_unavailable(_cls))

    # moviepy.editor 子模块占位
    _mp_editor = sys.modules.get("moviepy.editor")
    if _mp_editor is not None:
        for _cls in ("AudioFileClip", "VideoFileClip", "ImageClip",
                     "CompositeVideoClip", "TextClip", "ColorClip"):
            if not hasattr(_mp_editor, _cls):
                setattr(
                    _mp_editor,
                    _cls,
                    _mp_unavailable(_cls),
                )

    # moviepy.audio 子模块
    _mp_audio = sys.modules.get("moviepy.audio")
    if _mp_audio is not None and not hasattr(_mp_audio, "AudioFileClip"):
        _mp_audio.AudioFileClip = _mp_unavailable("AudioFileClip")  # type: ignore[attr-defined]

    # 在 podcast_creator stub 上提供占位符（configure/create_podcast），
    # 这样 `from podcast_creator import configure, create_podcast` 才能成功
    # 而真正的业务调用会得到 ImportError 提示该功能不可用。
    _pc_stub = sys.modules.get("podcast_creator")
    if _pc_stub is not None:
        def _stub_configure(*args, **kwargs):
            raise ImportError(
                "podcast_creator is not available in desktop build"
            )

        def _stub_create_podcast(*args, **kwargs):
            raise ImportError(
                "podcast_creator is not available in desktop build"
            )

        def _stub_get_config(*args, **kwargs):
            return None

        if not hasattr(_pc_stub, "configure"):
            _pc_stub.configure = _stub_configure  # type: ignore[attr-defined]
        if not hasattr(_pc_stub, "create_podcast"):
            _pc_stub.create_podcast = _stub_create_podcast  # type: ignore[attr-defined]
        if not hasattr(_pc_stub, "get_config"):
            _pc_stub.get_config = _stub_get_config  # type: ignore[attr-defined]

    # === 修补 surrealdb 连接在 PyInstaller 下的兼容性问题 ===
    try:
        from surrealdb.connections.async_ws import AsyncWsSurrealConnection
        # 1. 添加 close 方法（基类抛 NotImplementedError）
        if "close" not in AsyncWsSurrealConnection.__dict__:
            async def _ws_close(self):
                try:
                    if getattr(self, "recv_task", None) is not None:
                        self.recv_task.cancel()
                    if getattr(self, "socket", None) is not None:
                        await self.socket.close()
                except Exception:
                    pass
                finally:
                    self.socket = None
                    for fut in getattr(self, "qry", {}).values():
                        if not fut.done():
                            fut.cancel()
                    self.qry.clear()
            AsyncWsSurrealConnection.close = _ws_close

        # 2. 修补 _send 方法处理 KeyError（recv_task 清理竞态条件）
        if hasattr(AsyncWsSurrealConnection, "_send"):
            _orig_send = AsyncWsSurrealConnection._send
            async def _safe_send(self, message, process, bypass=False):
                try:
                    return await _orig_send(self, message, process, bypass)
                except KeyError:
                    # recv_task 在等待响应时清理了 qry dict，重试一次
                    raise RuntimeError(f"SurrealDB connection lost during {process}")
            AsyncWsSurrealConnection._send = _safe_send
    except Exception:
        pass

    # 同时保留 HTTP close 补丁（以防回退到 HTTP）
    try:
        from surrealdb.connections.async_http import AsyncHttpSurrealConnection
        if "close" not in AsyncHttpSurrealConnection.__dict__:
            async def _http_close(self):
                if getattr(self, "_session", None) is not None:
                    await self._session.close()
                    self._session = None
            AsyncHttpSurrealConnection.close = _http_close
    except Exception:
        pass

# 关键：在 PyInstaller --onefile 模式下，资源被解压到临时目录
# 使用 sys._MEIPASS 获取资源路径
def get_resource_path(relative_path: str) -> Path:
    """获取资源文件路径（兼容 PyInstaller 打包）"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后的临时目录
        return Path(sys._MEIPASS) / relative_path
    # 开发模式：相对于项目根目录
    return Path(__file__).parent / relative_path


# 将项目根目录添加到 Python 路径（PyInstaller 模式下必要）
if hasattr(sys, "_MEIPASS"):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# 确保子包可被导入
parent = project_root.parent if hasattr(sys, "_MEIPASS") else project_root.parent
if str(parent) not in sys.path:
    sys.path.insert(0, str(parent))


def get_data_dir() -> Path:
    """获取用户数据目录（持久化数据）"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "OpenNotebook"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_surreal_port() -> int:
    """获取 SurrealDB 端口（从环境变量或默认值）"""
    return int(os.environ.get("SURREAL_PORT", "8500"))


def get_api_port() -> int:
    """获取 API 端口（从环境变量或默认值）"""
    return int(os.environ.get("API_PORT", "8502"))


def _configure_content_core_fallback() -> None:
    """为冻结环境准备 content_core 配置兜底。"""
    bundled_models = get_resource_path("content_core/models_config.yaml")
    bundled_cc = get_resource_path("content_core/cc_config.yaml")
    if bundled_models.exists() and bundled_cc.exists():
        return

    fallback_dir = get_data_dir() / "content_core"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback_path = fallback_dir / "models_config.yaml"
    if not fallback_path.exists():
        fallback_path.write_text(
            """speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    top_p: 1
    max_tokens: 2000
    timeout: 300

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    output_format: json
    timeout: 600

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    top_p: 1
    max_tokens: 2000
    timeout: 300
""",
            encoding="utf-8",
        )

    os.environ.setdefault("CCORE_MODEL_CONFIG_PATH", str(fallback_path))
    os.environ.setdefault("CCORE_CONFIG_PATH", str(fallback_path))


def _configure_content_core_fallback() -> None:
    """为冻结环境准备 content_core 配置兜底。"""
    bundled_models = get_resource_path("content_core/models_config.yaml")
    bundled_cc = get_resource_path("content_core/cc_config.yaml")
    if bundled_models.exists() and bundled_cc.exists():
        return

    fallback_dir = get_data_dir() / "content_core"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback_path = fallback_dir / "models_config.yaml"
    if not fallback_path.exists():
        fallback_path.write_text(
            """speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    top_p: 1
    max_tokens: 2000
    timeout: 300

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    output_format: json
    timeout: 600

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    top_p: 1
    max_tokens: 2000
    timeout: 300
""",
            encoding="utf-8",
        )

    os.environ.setdefault("CCORE_MODEL_CONFIG_PATH", str(fallback_path))
    os.environ.setdefault("CCORE_CONFIG_PATH", str(fallback_path))


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def wait_for_port(port: int, timeout: float = 30.0) -> bool:
    """等待端口开始监听"""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.3)
    return False


class SurrealProcess:
    """SurrealDB 嵌入式进程管理器"""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.port = get_surreal_port()
        self.data_dir = get_data_dir() / "surreal_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # 将 surreal.exe 复制到永久目录，避免依赖 _MEI 临时目录
        self._bin_dir = get_data_dir() / "bin"
        self._bin_dir.mkdir(parents=True, exist_ok=True)
        self._local_surreal = self._bin_dir / "surreal.exe"

    def _ensure_surreal_binary(self) -> Path | None:
        """确保 surreal.exe 在永久目录中存在（从 _MEIPASS 复制）"""
        try:
            # 1. 优先使用已复制的副本
            if self._local_surreal.exists():
                return self._local_surreal
            # 2. 从 _MEIPASS 复制
            bundled = get_resource_path("surreal.exe")
            if bundled.exists():
                shutil.copy2(str(bundled), str(self._local_surreal))
                return self._local_surreal
            # 3. 开发模式：使用项目根目录下的 surreal.exe
            dev_surreal = Path(__file__).parent / "surreal.exe"
            if dev_surreal.exists():
                shutil.copy2(str(dev_surreal), str(self._local_surreal))
                return self._local_surreal
            logger.error("surreal.exe not found in bundle or project root")
            return None
        except Exception as e:
            logger.error(f"Failed to prepare surreal.exe: {e}")
            return None

    def start(self) -> bool:
        """启动 SurrealDB 进程"""
        if not is_port_in_use(self.port):
            surreal_exe = self._ensure_surreal_binary()
            if surreal_exe is None or not surreal_exe.exists():
                logger.error("SurrealDB binary unavailable")
                return False

            # 嵌入式：使用文件存储，用户名/密码固定
            cmd = [
                str(surreal_exe),
                "start",
                "--bind", f"127.0.0.1:{self.port}",
                "--user", "root",
                "--pass", "root",
                "--allow-guests",
                "file:" + str(self.data_dir / "db").replace("\\", "/"),
            ]
            logger.info(f"Starting SurrealDB: {' '.join(cmd)}")
            try:
                # 将 stderr 写入日志文件用于诊断，stdout 丢弃
                # 注意：使用 PIPE 但不读取会导致管道满阻塞，所以用 DEVNULL
                surreal_log = get_data_dir() / "surreal.log"
                surreal_err = open(surreal_log, "w", encoding="utf-8")
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=surreal_err,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    cwd=str(self._bin_dir),
                )
            except Exception as e:
                logger.error(f"Failed to launch SurrealDB: {e}")
                return False
            atexit.register(self.stop)

            if wait_for_port(self.port, timeout=20.0):
                logger.info(f"SurrealDB started on port {self.port}")
                return True
            else:
                # 读取日志文件帮助诊断
                try:
                    surreal_err.close()
                    if surreal_log.exists():
                        log_content = surreal_log.read_text(encoding="utf-8", errors="ignore")[:500]
                        logger.error(f"SurrealDB log: {log_content}")
                except Exception:
                    pass
                logger.error("SurrealDB failed to start within timeout")
                self.stop()
                return False
        else:
            logger.info(f"Port {self.port} already in use, assuming SurrealDB is running")
            return True

    def stop(self):
        """停止 SurrealDB 进程"""
        if self.process:
            logger.info("Stopping SurrealDB...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self.process.kill()
                except OSError:
                    pass
            self.process = None
            logger.info("SurrealDB stopped")


class ApiServer:
    """FastAPI 服务器管理器"""

    def __init__(self, surreal_port: int):
        self.port = get_api_port()
        self.surreal_port = surreal_port
        self.process: subprocess.Popen | None = None
        self.startup_log: Path = get_data_dir() / "api-startup.log"
        self.startup_err: Path = get_data_dir() / "api-startup.log.err"

    def start(self):
        """在新线程中启动 FastAPI"""
        # 配置环境变量
        os.environ["SURREAL_URL"] = f"ws://127.0.0.1:{self.surreal_port}"
        os.environ["SURREAL_USER"] = "root"
        os.environ["SURREAL_PASSWORD"] = "root"
        os.environ["SURREAL_NAMESPACE"] = "open_notebook"
        os.environ["SURREAL_DATABASE"] = "open_notebook"
        os.environ["API_HOST"] = "127.0.0.1"
        os.environ["API_PORT"] = str(self.port)
        child_env = os.environ.copy()

        if hasattr(sys, "_MEIPASS"):
            os.chdir(sys._MEIPASS)

        child_args = [sys.executable, "--api-child"]
        logger.info(f"Starting API child process: {' '.join(child_args)}")
        try:
            self.startup_log.parent.mkdir(parents=True, exist_ok=True)
            self.process = subprocess.Popen(
                child_args,
                stdout=subprocess.DEVNULL,
                stderr=open(self.startup_err, "a", encoding="utf-8"),
                cwd=str(Path(sys.executable).parent),
                env=child_env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            atexit.register(self.stop)
        except Exception as e:
            logger.exception(f"Failed to spawn API child process: {e}")
            raise

        logger.info(f"API server starting on port {self.port}")

    def wait_ready(self, timeout: float = 180.0) -> bool:
        """等待 API 就绪"""
        start = time.time()
        health_url = f"http://127.0.0.1:{self.port}/health"
        while time.time() - start < timeout:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"API child exited with code {self.process.returncode}")
            try:
                import urllib.request

                with urllib.request.urlopen(health_url, timeout=1.0) as response:
                    if 200 <= getattr(response, "status", 0) < 300:
                        return True
            except Exception:
                pass
            if wait_for_port(self.port, timeout=0.2):
                # 端口已被绑定，但健康检查还没完全通过，继续轮询。
                pass
            time.sleep(0.3)
        return False

    def stop(self):
        """停止 API 子进程"""
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                self.process.kill()
            except OSError:
                pass
        self.process = None


def run_gui_mode():
    """GUI 模式：启动后端并打开 UI

    UI 加载策略（按可靠性排序）：
    1. **系统默认浏览器** (webbrowser.open) — 最可靠，跨平台一致
    2. pywebview 嵌入窗口 — 可选，需 WebView2 Runtime（很多机器未装）
    3. 仅运行后端，在 cmd 窗口打印 URL 让用户手动打开
    """
    diag_log = Path(os.environ.get("APPDATA", Path.home())) / "OpenNotebook" / "startup.log"
    diag_log.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        try:
            with open(diag_log, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except Exception:
            pass
        try:
            logger.info(msg)
        except Exception:
            pass
        try:
            print(msg, file=sys.stderr, flush=True)
        except Exception:
            pass

    log("=== Open Notebook Desktop starting ===")
    log(f"  sys.executable = {sys.executable}")
    log(f"  sys._MEIPASS  = {getattr(sys, '_MEIPASS', '<not frozen>')}")
    log(f"  api_port      = {get_api_port()}")
    log(f"  surreal_port  = {get_surreal_port()}")
    _configure_content_core_fallback()

    # 1. 启动 SurrealDB
    surreal = SurrealProcess()
    log("Starting SurrealDB...")
    if not surreal.start():
        log("ERROR: SurrealDB failed to start")
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)
    log(f"SurrealDB ready on port {surreal.port}")

    # 2. 启动 API
    api = ApiServer(surreal.port)
    log("Starting API server...")
    api.start()
    if not api.wait_ready(timeout=180):
        log("ERROR: API server failed to start (timeout 180s)")
        surreal.stop()
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)
    log(f"API ready on port {api.port}")
    log(f"  → http://127.0.0.1:{api.port}")

    url = f"http://127.0.0.1:{api.port}"

    # 3. 打开 UI：优先尝试原生窗口，浏览器作为兜底
    opened_via = None
    error_chains = []

    # === 主路径: pywebview 嵌入窗口（更像桌面应用） ===
    try:
        log("[UI] 尝试启动嵌入式 WebView 窗口 (pywebview)...")
        import webview  # type: ignore
        try:
            window = webview.create_window(  # noqa: F841
                title="Open Notebook",
                url=url,
                width=1280,
                height=800,
                min_size=(1024, 700),
                resizable=True,
                text_select=True,
            )
            log("[UI] 启动 WebView 事件循环 (阻塞直到窗口关闭)...")
            webview.start()
            log("[UI] WebView 窗口已关闭")
            opened_via = "pywebview"
        except Exception as inner_e:
            error_chains.append(f"pywebview create/start: {type(inner_e).__name__}: {inner_e}")
            log(f"[UI] ✗ pywebview 启动失败: {type(inner_e).__name__}: {inner_e}")
    except Exception as e:
        error_chains.append(f"pywebview import: {e}")
        log(f"[UI] ✗ pywebview 未安装/未打包: {e}")

    # === 备选: 系统默认浏览器 ===
    if opened_via is None:
        try:
            log(f"[UI] 回退到系统默认浏览器打开 {url} ...")
            import webbrowser  # type: ignore
            ok = webbrowser.open(url, new=2)
            if ok:
                log("[UI] ✓ 已请求系统默认浏览器打开 URL")
                opened_via = "webbrowser"
            else:
                error_chains.append("webbrowser.open returned False (no default browser)")
                log("[UI] ✗ webbrowser.open 返回 False (无默认浏览器)")
        except Exception as e:
            error_chains.append(f"webbrowser: {e}")
            log(f"[UI] ✗ webbrowser 异常: {e}")

    # === 兜底: 打印 URL + 维持进程存活 ===
    if opened_via is None:
        log("=" * 60)
        log("自动打开 UI 失败！请手动复制以下地址到浏览器打开：")
        log(f"    {url}")
        log("=" * 60)
        log("关闭本窗口将关闭 Open Notebook 服务。")

    # 维持进程存活，直到用户主动关闭
    try:
        log("[MAIN] 服务运行中，按 Ctrl+C 关闭...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("[MAIN] 收到 KeyboardInterrupt，开始关闭...")
    finally:
        log("[MAIN] Shutting down...")
        surreal.stop()
        log("=== Open Notebook Desktop stopped ===")


def run_console_mode():
    """控制台模式：仅启动后端，用于调试或无界面环境"""
    surreal = SurrealProcess()
    if not surreal.start():
        sys.exit(1)
    api = ApiServer(surreal.port)
    api.start()
    api.wait_ready()
    print(f"Open Notebook running at http://127.0.0.1:{api.port}")
    print("Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        surreal.stop()


def run_api_child_mode():
    """API 子进程模式：仅负责启动 FastAPI。"""
    import uvicorn
    from api.desktop_main import app

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=get_api_port(),
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    # 最早期诊断日志（在 logger 配置之前）
    import tempfile as _tf
    _diag = Path(os.environ.get("APPDATA", Path.home())) / "OpenNotebook" / "startup.log"
    _diag.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_diag, "w", encoding="utf-8") as _f:
            _f.write(f"[{time.strftime('%H:%M:%S')}] EXE entry_point starting\n")
            _f.write(f"sys.executable: {sys.executable}\n")
            _f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'NOT SET')}\n")
            _f.write(f"argv: {sys.argv}\n")
    except Exception:
        pass

    # 配置日志
    logger.remove()
    logger.add(
        _diag.parent / "app.log",
        level="INFO",
        format="{time:HH:mm:ss} | {level} | {message}",
        encoding="utf-8",
        rotation="5 MB",
        retention=3,
    )
    if sys.stderr is not None:
        logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

    if "--console" in sys.argv:
        run_console_mode()
    elif "--api-child" in sys.argv:
        run_api_child_mode()
    else:
        run_gui_mode()
