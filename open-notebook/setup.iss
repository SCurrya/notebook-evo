; Open Notebook Windows Installer Script
; 生成符合行业标准的 Windows 安装包

#define MyAppName "Open Notebook"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Open Notebook Project"
#define MyAppURL "https://github.com/nicobailon/open-notebook"
#define MyAppExeName "OpenNotebook.exe"

[Setup]
AppId={{8F7B5E3A-2D1C-4B6F-9E8A-3C5D7B1E0F2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=open-notebook-setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
DisableDirPage=no
DisableReadyPage=no
LicenseFile=
InfoBeforeFile=
SetupIconFile=
; LZMA2 压缩配置
LZMAUseSeparateProcess=yes
LZMADictionarySize=1048576
LZMANumFastBytes=273

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
; 主 EXE 文件（PyInstaller 打包的 onedir 产物）
Source: "dist\OpenNotebook\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载时停止运行中的进程
Filename: "{cmd}"; Parameters: "/c taskkill /f /im {#MyAppExeName} 2>nul & taskkill /f /im surreal.exe 2>nul"; Flags: runhidden; RunOnceId: "KillProcess"

[UninstallDelete]
; 清理用户数据目录（可选）
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // 检查是否已有实例运行，尝试停止
  Exec(ExpandConstant('{cmd}'), '/c taskkill /f /im OpenNotebook.exe 2>nul & taskkill /f /im surreal.exe 2>nul', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // 安装前确保旧进程已停止
  Exec(ExpandConstant('{cmd}'), '/c taskkill /f /im OpenNotebook.exe 2>nul & taskkill /f /im surreal.exe 2>nul', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
