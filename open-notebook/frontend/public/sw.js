/**
 * Open Notebook Service Worker
 *
 * 缓存策略：stale-while-revalidate
 * - 导航请求优先使用缓存，同时后台更新
 * - 静态资源使用缓存优先，后台更新
 * - API 请求始终网络优先，失败时回退缓存
 * - 支持离线浏览已缓存页面
 */

const CACHE_VERSION = 'open-notebook-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const API_CACHE = `${CACHE_VERSION}-api`;

// 需要预缓存的核心资源
const PRECACHE_URLS = ['/', '/manifest.json', '/logo.svg'];

// API 路径前缀（网络优先）
const API_PREFIX = '/api/';

// 静态资源路径模式
const STATIC_ASSET_PATTERN = /\.(?:js|css|woff2?|ttf|png|jpg|jpeg|svg|gif|webp|ico)$/i;

/**
 * 安装阶段：预缓存核心资源并立即激活
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

/**
 * 激活阶段：清理旧版本缓存
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => !name.startsWith(CACHE_VERSION))
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

/**
 * stale-while-revalidate 策略：
 * 立即返回缓存，同时后台拉取最新资源更新缓存。
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((networkResponse) => {
      // 仅缓存成功的响应
      if (networkResponse && networkResponse.status === 200) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch(() => cachedResponse);

  // 有缓存则立即返回，否则等待网络响应
  return cachedResponse || fetchPromise;
}

/**
 * 网络优先策略：API 请求优先走网络，失败时回退缓存。
 */
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

/**
 * 请求拦截：根据请求类型分发到不同缓存策略
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // 仅处理 GET 请求
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // 跳过跨域请求
  if (url.origin !== self.location.origin) return;

  // API 请求：网络优先
  if (url.pathname.startsWith(API_PREFIX)) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // 导航请求（HTML 页面）：stale-while-revalidate
  if (request.mode === 'navigate') {
    event.respondWith(staleWhileRevalidate(request, PAGE_CACHE));
    return;
  }

  // 静态资源：stale-while-revalidate
  if (STATIC_ASSET_PATTERN.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  // 其他 GET 请求：默认 stale-while-revalidate
  event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
});

/**
 * 消息通信：支持前端触发 SW 立即激活
 */
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
