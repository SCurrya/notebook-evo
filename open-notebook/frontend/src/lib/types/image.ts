/**
 * Image generation types.
 *
 * Integrates with the open-notebook backend at /api/images, which
 * supports multiple providers (OpenAI DALL-E, Stability AI, and an
 * offline Pillow-based placeholder).
 */

/** Supported image generation providers. */
export type ImageProvider = 'openai' | 'stable_diffusion' | 'placeholder'

/** Request payload for image generation. */
export interface ImageGenerationRequest {
  /** Text prompt describing the image (required). */
  prompt: string
  /** What to exclude from the image (stable_diffusion only). */
  negative_prompt?: string
  /** Image dimensions: 256x256, 512x512, 1024x1024, 1792x1024, 1024x1792. */
  size: string
  /** Image quality: standard, hd (DALL-E 3 only). */
  quality: string
  /** Image style: vivid, natural (DALL-E 3 only). */
  style: string
  /** Number of images to generate (1-4). */
  n: number
  /** Image generation provider. */
  provider: ImageProvider
  /** Model name: dall-e-3, dall-e-2 (openai provider only). */
  model?: string
}

/** A single generated image within a task. */
export interface GeneratedImage {
  index: number
  filename: string
  /** Relative URL for downloading the full image. */
  url: string
  /** Base64-encoded JPEG thumbnail for quick preview. */
  thumbnail_base64: string
  width: number
  height: number
}

/** Immediate response from a generation request. */
export interface ImageGenerationResponse {
  task_id: string
  status: string
  message: string
}

/** Task lifecycle states. */
export type ImageTaskState =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'

/** Full status of an image generation task. */
export interface ImageTaskStatus {
  id: string
  state: ImageTaskState
  progress: number
  message: string
  prompt: string
  provider: string
  model?: string | null
  size: string
  n: number
  images: GeneratedImage[]
  created_at: string
  updated_at: string
  error?: string | null
}

/** Information about an available image provider. */
export interface ImageProviderInfo {
  id: string
  name: string
  available: boolean
  models: string[]
  description: string
  requires_api_key: boolean
}

/** Paginated list of image tasks. */
export interface ImageTaskListResponse {
  items: ImageTaskStatus[]
  total: number
  page: number
  page_size: number
}
