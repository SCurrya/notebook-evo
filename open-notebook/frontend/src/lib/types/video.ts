/**
 * Video generation types.
 *
 * Integrates with MoneyPrinterTurbo microservice via the open-notebook
 * backend proxy at /api/videos.
 */

export type VideoAspect = '16:9' | '9:16' | '1:1'

export type VideoConcatMode = 'sequential' | 'random' | 'sequential_desc'

export type VideoSource = 'pexels' | 'pixabay' | 'local'

export type SubtitlePosition = 'top' | 'center' | 'bottom' | 'custom'

export interface VideoVoiceConfig {
  voice_name: string
  voice_rate: number
  voice_volume: number
}

export interface VideoSubtitleConfig {
  enabled: boolean
  font_name: string
  font_size: number
  text_color: string
  stroke_color: string
  stroke_width: number
  position: SubtitlePosition
  custom_position: number
}

export interface VideoGenerationRequest {
  video_subject: string
  video_script?: string
  language: string
  video_aspect: VideoAspect
  paragraph_number: number
  custom_system_prompt?: string
  voice: VideoVoiceConfig
  subtitle: VideoSubtitleConfig
  video_source: VideoSource
  max_clip_duration: number
  video_concat_mode: VideoConcatMode
  bgm_type: string
  max_concurrent_tasks?: number
}

export interface VideoTaskResponse {
  task_id: string
  status: string
  message: string
}

export type VideoTaskState =
  | 'pending'
  | 'processing'
  | 'downloading_materials'
  | 'generating_script'
  | 'generating_audio'
  | 'generating_subtitle'
  | 'generating_video'
  | 'completed'
  | 'failed'
  | 'unknown'

export interface VideoTaskStatus {
  id: string
  state: VideoTaskState
  progress: number
  message: string
  video_url?: string | null
  video_path?: string | null
  script?: string | null
  terms?: string[] | null
  audio_url?: string | null
  subtitle_url?: string | null
  created_at?: string | null
  updated_at?: string | null
  error?: string | null
}

export interface VideoServiceHealth {
  available: boolean
  url: string
  status: 'healthy' | 'unavailable'
  error?: string
}

export interface VideoTaskListResponse {
  items: VideoTaskStatus[]
  total: number
  page: number
  page_size: number
}

/**
 * 视频模板预设配置。
 *
 * 每个模板针对特定场景预设了节奏、配音、BGM、字幕等参数，
 * 用户可基于模板快速创建视频任务并按需覆盖部分参数。
 */
export interface VideoTemplate {
  /** 模板唯一标识 (marketing/tutorial/story/news/short) */
  key: string
  /** 模板展示名称 */
  name: string
  /** 模板适用场景描述 */
  description: string
  /** 脚本段落数 */
  paragraph_number: number
  /** Azure TTS 语音名称 */
  voice_name: string
  /** BGM 选择: random/none/<filename> */
  bgm_type: string
  /** 视频宽高比: 16:9/9:16/1:1 */
  video_aspect: VideoAspect
  /** 字幕字体大小 */
  subtitle_font_size: number
  /** 拼接模式: sequential/random/sequential_desc */
  video_concat_mode: VideoConcatMode
  /** 单段素材最大时长 (秒) */
  max_clip_duration: number
}

/**
 * 视频模板列表响应。
 */
export type VideoTemplateListResponse = VideoTemplate[]

/**
 * 从模板创建视频任务的请求体。
 */
export interface TemplateCreateRequest {
  /** 模板标识: marketing/tutorial/story/news/short */
  template_name: string
  /** 视频主题/标题 */
  subject: string
  /** 覆盖模板预设参数，支持 VideoGenerationRequest 的任意字段 */
  custom_overrides?: Partial<VideoGenerationRequest>
}
