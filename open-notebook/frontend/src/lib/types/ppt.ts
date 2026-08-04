/**
 * PPT 生成类型定义。
 *
 * 对应后端 /api/ppt 端点，使用 python-pptx 生成 .pptx 文件。
 */

/** PPT 模板类型 */
export type PPTTemplateType =
  | 'default'
  | 'business'
  | 'tech'
  | 'education'
  | 'creative'

/** 幻灯片布局类型 */
export type PPTSlideLayout =
  | 'title_content'
  | 'title_only'
  | 'content_only'
  | 'image'

/** 单张幻灯片内容 */
export interface PPTSlide {
  /** 幻灯片标题 */
  title: string
  /** 内容条目（bullet points） */
  content: string[]
  /** 图片 URL（http/https） */
  image_url?: string | null
  /** 图片 base64 编码（可含 data URI 前缀） */
  image_base64?: string | null
  /** 布局类型 */
  layout: PPTSlideLayout
}

/** PPT 生成请求 */
export interface PPTGenerationRequest {
  /** 演示文稿标题（用于标题幻灯片） */
  title: string
  /** 副标题 */
  subtitle?: string | null
  /** 作者 */
  author?: string | null
  /** 日期字符串 */
  date?: string | null
  /** 模板类型 */
  template: PPTTemplateType
  /** Markdown 内容（## 作为新幻灯片标题，- / * 作为 bullet） */
  markdown_content?: string | null
  /** 显式幻灯片列表（若提供则与 markdown 合并） */
  slides?: PPTSlide[] | null
}

/** 模板信息（用于前端展示） */
export interface PPTTemplate {
  /** 模板 ID */
  id: PPTTemplateType
  /** 模板名称 */
  name: string
  /** 模板描述 */
  description: string
  /** 前端用于渐变预览的颜色（hex 字符串） */
  preview_colors: string[]
  /** 强调色（hex） */
  accent_color: string
}

/** 生成任务提交响应 */
export interface PPTTaskResponse {
  task_id: string
  status: string
  message: string
}

/** PPT 任务状态 */
export type PPTTaskState =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'

/** PPT 任务状态详情 */
export interface PPTTaskStatus {
  id: string
  state: PPTTaskState
  progress: number
  message: string
  file_path?: string | null
  download_url?: string | null
  created_at: string
  updated_at?: string | null
  completed_at?: string | null
  error?: string | null
  template?: string | null
  title?: string | null
  slide_count?: number | null
}

/** 任务列表分页响应 */
export interface PPTTaskListResponse {
  items: PPTTaskStatus[]
  total: number
  page: number
  page_size: number
}
