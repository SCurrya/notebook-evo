# Aurora Knowledge 设计系统规范

> Open Notebook 高级 UI 设计系统 - 融合 Material Design 3 表达力与玻璃拟态质感

---

## 1. 品牌理念

**Aurora Knowledge**（极光知识）设计语言以「知识与洞察」为核心品牌价值：

- **靛紫主色**（Indigo Violet）象征智慧、深度与专注
- **琥珀强调色**（Warm Amber）代表灵感、温暖与创造力
- **极光渐变**将两者融合，寓意知识从吸收到产出的转化过程

### 设计原则

| 原则 | 描述 |
|------|------|
| **层次分明** | 通过 5 级阴影系统建立清晰的空间层次 |
| **流动自然** | Material 3 缓动曲线，所有过渡都有物理感 |
| **品牌一致** | 渐变元素贯穿全局，形成统一视觉语言 |
| **无障碍** | OKLCH 色彩空间确保感知均匀，WCAG AA 对比度 |
| **移动优先** | 48px 触摸目标、安全区域适配、响应式断点 |

---

## 2. 色彩系统

### 2.1 主色板

所有颜色使用 **OKLCH 色彩空间**，确保感知亮度均匀。

| Token | 亮色值 | 暗色值 | 用途 |
|-------|--------|--------|------|
| `--primary` | `oklch(0.55 0.25 280)` | `oklch(0.65 0.22 280)` | 主品牌色（靛紫） |
| `--secondary` | `oklch(0.95 0.015 290)` | `oklch(0.24 0.012 285)` | 次要背景 |
| `--accent` | `oklch(0.94 0.02 290)` | `oklch(0.28 0.02 290)` | 悬停高亮 |
| `--destructive` | `oklch(0.58 0.24 25)` | `oklch(0.7 0.19 25)` | 危险操作（珊瑚红） |
| `--success` | `oklch(0.62 0.19 155)` | `oklch(0.7 0.17 155)` | 成功状态（翡翠绿） |
| `--warning` | `oklch(0.75 0.18 70)` | `oklch(0.8 0.16 70)` | 警告状态（琥珀色） |
| `--info` | `oklch(0.62 0.15 230)` | `oklch(0.7 0.14 230)` | 信息状态（天蓝色） |

### 2.2 中性色

基于色相 285°（微暖灰），从纯白到近黑的完整灰阶：

| Token | 亮色 | 暗色 |
|-------|------|------|
| `--background` | `oklch(0.99 0.002 285)` | `oklch(0.15 0.008 285)` |
| `--foreground` | `oklch(0.18 0.01 285)` | `oklch(0.96 0.005 285)` |
| `--muted` | `oklch(0.96 0.005 285)` | `oklch(0.24 0.012 285)` |
| `--muted-foreground` | `oklch(0.52 0.015 285)` | `oklch(0.68 0.012 285)` |
| `--border` | `oklch(0.91 0.005 285)` | `oklch(1 0 0 / 8%)` |
| `--card` | `oklch(1 0 0)` | `oklch(0.19 0.01 285)` |

### 2.3 品牌渐变

```css
--gradient-primary: linear-gradient(135deg, 靛紫 → 紫罗兰)
--gradient-accent:  linear-gradient(135deg, 琥珀 → 橙红)
--gradient-surface: linear-gradient(180deg, 白 → 微灰)
--gradient-hero:    linear-gradient(135deg, 靛紫/8% → 琥珀/5%)
```

### 2.4 图表色板

| 序号 | 亮色 | 暗色 | 色相 |
|------|------|------|------|
| chart-1 | 靛紫 | 亮靛紫 | 280° |
| chart-2 | 翡翠 | 亮翡翠 | 155° |
| chart-3 | 琥珀 | 亮琥珀 | 70° |
| chart-4 | 天蓝 | 亮天蓝 | 230° |
| chart-5 | 玫红 | 亮玫红 | 340° |

---

## 3. 排版系统

### 3.1 字体族

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', ...
--font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', ...
--font-display: 'Inter', -apple-system, BlinkMacSystemFont, ...
```

- **主字体**：Inter（首选），回退到系统字体栈
- **等宽字体**：SF Mono / Monaco / Cascadia Code
- **Display 字体**：用于标题，与主字体相同但应用 `tracking-tight`

### 3.2 字号层级

| 用途 | 类名 | 尺寸 | 字重 |
|------|------|------|------|
| 页面标题 | `text-3xl` | 30px | `font-bold` |
| 区块标题 | `text-lg` | 18px | `font-semibold` |
| 卡片标题 | `text-base` | 16px | `font-semibold` |
| 正文 | `text-sm` | 14px | `font-medium` |
| 辅助文本 | `text-xs` | 12px | `font-medium` |
| 统计数值 | `text-2xl` | 24px | `font-bold` |

### 3.3 字体特性

```css
font-feature-settings: 'cv11', 'ss01', 'ss03';  /* Inter 优化 */
text-rendering: optimizeLegibility;
```

- 标题使用 `text-wrap: balance`（文本平衡换行）
- 段落使用 `text-wrap: pretty`（美观换行）
- 全局 `antialiased` 字体平滑

---

## 4. 间距与圆角

### 4.1 圆角系统（Material 3 风格）

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-xs` | 0.25rem (4px) | 小元素（Badge） |
| `--radius-sm` | 0.375rem (6px) | 按钮、输入框 |
| `--radius-md` | 0.625rem (10px) | 中型元素 |
| `--radius-lg` | 0.75rem (12px) | 卡片（默认） |
| `--radius-xl` | 1rem (16px) | 大卡片 |
| `--radius-2xl` | 1.25rem (20px) | 模态框 |
| `--radius-3xl` | 1.5rem (24px) | 特殊容器 |
| `--radius-full` | 9999px | 圆形元素 |

### 4.2 页面间距

| 断点 | 容器内边距 |
|------|-----------|
| 移动端 (<640px) | `px-4` (16px) |
| 平板 (640-1024px) | `px-6` (24px) |
| 桌面 (≥1024px) | `px-8` (32px) |

---

## 5. 阴影系统（Material 3 Elevation）

5 级阴影系统，模拟真实物理光照：

| 级别 | 类名 | 亮色阴影 | 用途 |
|------|------|---------|------|
| 1 | `.elevation-1` | `0 1px 2px /6%, 0 1px 3px /4%` | 按钮、输入框 |
| 2 | `.elevation-2` | `0 2px 4px /8%, 0 4px 6px /5%` | 卡片悬停 |
| 3 | `.elevation-3` | `0 4px 8px /10%, 0 8px 12px /6%` | 浮层、下拉 |
| 4 | `.elevation-4` | `0 8px 16px /12%, 0 16px 24px /8%` | 对话框 |
| 5 | `.elevation-5` | `0 16px 32px /14%, 0 32px 48px /10%` | 全屏模态 |

暗色模式阴影使用 `oklch(0 0 0 / x)` 纯黑透明度，更深沉。

---

## 6. 动画系统

### 6.1 缓动函数（Material 3）

| 名称 | 贝塞尔曲线 | 用途 |
|------|-----------|------|
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | 标准过渡 |
| `--ease-emphasized` | `cubic-bezier(0.3, 0, 0, 1)` | 强调过渡 |
| `--ease-decelerated` | `cubic-bezier(0, 0, 0, 1)` | 进入动画 |
| `--ease-accelerated` | `cubic-bezier(0.3, 0, 1, 1)` | 退出动画 |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 弹性效果 |

### 6.2 动画时长

| Token | 值 | 用途 |
|-------|-----|------|
| `--duration-instant` | 100ms | 即时反馈 |
| `--duration-fast` | 150ms | 快速过渡 |
| `--duration-normal` | 250ms | 标准过渡 |
| `--duration-slow` | 400ms | 页面动画 |
| `--duration-slower` | 600ms | 复杂动画 |

### 6.3 关键帧动画

| 类名 | 效果 | 用途 |
|------|------|------|
| `.animate-fade-in` | 淡入 | 页面进入 |
| `.animate-slide-up` | 上滑+淡入 | 内容进入 |
| `.animate-slide-down` | 下滑+淡入 | 错误提示 |
| `.animate-scale-in` | 缩放+淡入 | 模态框 |
| `.animate-slide-in-right` | 右滑+淡入 | 侧边面板 |
| `.animate-shimmer` | 闪光扫描 | 骨架屏 |
| `.animate-pulse-glow` | 脉冲发光 | 强调元素 |
| `.animate-gradient` | 渐变流动 | 动态背景 |
| `.animate-bounce-subtle` | 微弹跳 | 引导注意 |

### 6.4 交错动画

列表项依次出现的交错效果：

```html
<div class="stagger-item stagger-1">...</div>  <!-- 延迟 50ms -->
<div class="stagger-item stagger-2">...</div>  <!-- 延迟 100ms -->
<div class="stagger-item stagger-3">...</div>  <!-- 延迟 150ms -->
...最多 8 级
```

### 6.5 微交互

| 交互 | 效果 |
|------|------|
| 按钮按下 | `active:scale-[0.97]` 缩放反馈 |
| 卡片悬停 | `translateY(-2px)` + 阴影升级 |
| 侧边栏菜单 | 左侧 3px 渐变指示条滑入 |
| 主题切换 | `transition-colors` 平滑过渡 |

---

## 7. 组件库

### 7.1 Button 组件

| 变体 | 样式 | 用途 |
|------|------|------|
| `default` | 主色填充 + elevation-1 | 主操作 |
| `gradient` | 渐变填充 + elevation-2 | CTA 按钮 |
| `destructive` | 红色填充 | 危险操作 |
| `outline` | 边框 + 背景透明 | 次要操作 |
| `secondary` | 灰色填充 | 辅助操作 |
| `ghost` | 透明背景 | 工具栏按钮 |
| `glass` | 玻璃拟态 | 浮层按钮 |
| `link` | 文字链接 | 导航链接 |

| 尺寸 | 高度 | 用途 |
|------|------|------|
| `sm` | 32px | 紧凑布局 |
| `default` | 36px | 标准 |
| `lg` | 40px | 重要操作 |
| `xl` | 48px | 移动端 CTA |
| `icon` | 36×36px | 图标按钮 |
| `icon-sm` | 32×32px | 紧凑图标按钮 |
| `icon-lg` | 40×40px | 大图标按钮 |

### 7.2 Card 组件

- 默认 `elevation-1` 阴影
- `rounded-xl` 圆角
- 悬停时阴影升级（配合 `.card-hover`）
- 支持顶部渐变装饰线

### 7.3 PageHeader 组件

统一页面头部，包含：
- 渐变图标徽章
- 标题 + 描述
- 操作按钮区
- 可选统计卡片网格（2×4 响应式）

### 7.4 StatCard 组件

统计卡片，用于展示数据指标：
- 标签 + 数值 + 趋势
- 图标辅助
- 悬停阴影升级

### 7.5 Skeleton 组件

骨架屏加载状态：
- `Skeleton` - 基础骨架块
- `SkeletonText` - 多行文本骨架
- `SkeletonCard` - 卡片骨架

### 7.6 GlassCard 组件

玻璃拟态卡片：
- `GlassCard` - 标准玻璃效果（16px 模糊）
- `GlassCard strong` - 强玻璃效果（24px 模糊）
- `GradientBorderCard` - 渐变边框卡片

---

## 8. 响应式设计

### 8.1 断点系统

| 断点 | 宽度 | 用途 |
|------|------|------|
| 默认 | <640px | 移动端竖屏 |
| `sm` | ≥640px | 移动端横屏 / 小平板 |
| `md` | ≥768px | 平板竖屏 |
| `lg` | ≥1024px | 平板横屏 / 小桌面 |
| `xl` | ≥1280px | 桌面 |
| `2xl` | ≥1536px | 大桌面 |

### 8.2 移动端适配

- **触摸目标**：最小 48×48px（`.touch-target`）
- **安全区域**：`env(safe-area-inset-*)` 适配刘海屏
- **滚动条**：可隐藏（`.scrollbar-hide`）
- **侧边栏**：可折叠至 64px（`w-16`）

### 8.3 响应式网格

笔记本卡片网格：
- 移动端：1 列
- 平板：2 列
- 桌面：3 列

统计卡片网格：
- 移动端：2 列
- 桌面：4 列

---

## 9. 主题系统

### 9.1 三种模式

| 模式 | 描述 |
|------|------|
| `light` | Daylight Aurora - 日光极光 |
| `dark` | Midnight Aurora - 午夜极光 |
| `system` | 跟随系统偏好 |

### 9.2 实现机制

1. **Zustand Store** 持久化主题选择
2. **防闪烁脚本** 在 hydration 前应用主题
3. **ThemeProvider** 同步到 `document.documentElement`
4. **CSS 变量** 通过 `:root` 和 `.dark` 切换

### 9.3 暗色模式特点

- 背景从纯白变为深黑（`oklch(0.15)`）
- 边框使用白色透明度（`oklch(1 0 0 / 8%)`）
- 阴影更深沉（纯黑高透明度）
- 主色亮度提升（`0.55 → 0.65`）确保对比度
- `color-scheme: dark` 适配原生控件

---

## 10. 无障碍设计

### 10.1 对比度

所有文本颜色组合满足 WCAG AA 标准（4.5:1）：
- 主文本：`oklch(0.18)` on `oklch(0.99)` → 对比度 15:1
- 次要文本：`oklch(0.52)` on `oklch(0.99)` → 对比度 5.2:1

### 10.2 焦点可见性

- 所有交互元素 `focus-visible` 显示 3px 焦点环
- 焦点环颜色与主色一致
- `outline-ring/50` 半透明焦点环

### 10.3 动画偏好

```css
@media (prefers-reduced-motion: reduce) {
  /* 禁用所有动画 */
  animation-duration: 0.01ms !important;
  transition-duration: 0.01ms !important;
}
```

### 10.4 触摸目标

- 最小 48×48px（Material Design 标准）
- 间距充足，防止误触

---

## 11. 文件结构

```
src/
├── app/
│   └── globals.css              # 设计系统核心（Token + 工具类 + 动画）
├── components/
│   ├── ui/
│   │   ├── button.tsx           # 增强：gradient/glass 变体 + 按压反馈
│   │   ├── card.tsx             # 增强：elevation-1 默认阴影
│   │   ├── skeleton.tsx         # 新增：骨架屏组件
│   │   ├── page-header.tsx      # 新增：统一页面头部 + 统计卡片
│   │   ├── glass-card.tsx       # 新增：玻璃拟态卡片
│   │   └── ...                  # 其他 shadcn/ui 组件
│   ├── layout/
│   │   └── AppSidebar.tsx       # 增强：渐变 Logo + 活跃指示条
│   └── auth/
│       └── LoginForm.tsx        # 重设计：玻璃拟态 + 渐变背景
└── app/
    └── (dashboard)/
        ├── notebooks/page.tsx   # 重设计：PageHeader + 统计卡片
        ├── settings/page.tsx    # 重设计：PageHeader
        ├── sources/page.tsx     # 重设计：PageHeader
        ├── podcasts/page.tsx    # 重设计：PageHeader
        └── search/page.tsx      # 重设计：PageHeader
```

---

## 12. 设计 Token 速查

### CSS 变量

```css
/* 色彩 */
--primary, --secondary, --accent, --destructive
--success, --warning, --info
--background, --foreground, --card, --muted, --border

/* 渐变 */
--gradient-primary, --gradient-accent
--gradient-surface, --gradient-hero

/* 阴影 */
--shadow-elevation-1 ~ --shadow-elevation-5

/* 玻璃 */
--glass-bg, --glass-border, --glass-blur

/* 动画 */
--duration-instant ~ --duration-slower
--ease-standard, --ease-emphasized, --ease-spring

/* 圆角 */
--radius-xs ~ --radius-3xl, --radius-full
```

### 工具类

```css
/* 渐变 */
.gradient-primary, .gradient-accent, .gradient-surface, .gradient-hero
.text-gradient-primary

/* 阴影 */
.elevation-1 ~ .elevation-5

/* 玻璃 */
.glass, .glass-strong

/* 发光 */
.glow-primary

/* 动画 */
.animate-fade-in, .animate-slide-up, .animate-scale-in
.animate-shimmer, .animate-pulse-glow, .animate-gradient
.stagger-item, .stagger-1 ~ .stagger-8

/* 布局 */
.page-container, .page-content

/* 响应式 */
.safe-top, .safe-bottom, .touch-target, .scrollbar-hide
```

---

## 总结

Aurora Knowledge 设计系统为 Open Notebook 提供了：

1. **独特的品牌识别** - 靛紫+琥珀的极光渐变贯穿全局
2. **完整的视觉语言** - 色彩、排版、阴影、动画的系统性设计
3. **Material 3 兼容** - 5 级阴影、 expressive 缓动、触摸目标
4. **玻璃拟态质感** - 登录页和浮层的现代视觉体验
5. **流畅的交互动画** - 页面进入、列表交错、微交互反馈
6. **移动优先响应式** - 从手机到桌面的完整适配
7. **无障碍设计** - WCAG AA 对比度、焦点可见、动画偏好
8. **暗色模式** - 午夜极光主题，深沉而不失品牌色
