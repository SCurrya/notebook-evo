/**
 * PDF generation types.
 *
 * Generated server-side via reportlab (no browser printing). The backend
 * exposes /api/pdf/* endpoints for template discovery, async task
 * submission, status polling, and file download.
 */

/** Available PDF template IDs. */
export type PDFTemplateId =
  | 'report'
  | 'article'
  | 'resume'
  | 'letter'
  | 'ebook'

/** Supported page sizes. */
export type PDFPageSize = 'A4' | 'LETTER'

/** PDF template descriptor. */
export interface PDFTemplate {
  /** Unique template identifier, e.g. 'report'. */
  id: PDFTemplateId
  /** Human-readable template name. */
  name: string
  /** Description of the template's intended use. */
  description: string
  /** Page size: 'A4' or 'LETTER'. */
  page_size: PDFPageSize
  /** Whether the template supports two-column layout. */
  two_column: boolean
  /** Whether the template generates a cover page. */
  has_cover: boolean
  /** Whether the template generates a table of contents. */
  has_toc: boolean
  /** Whether the template includes header and footer. */
  has_header_footer: boolean
}

/** Request payload for PDF generation. */
export interface PDFGenerationRequest {
  /** Template ID to use. */
  template: PDFTemplateId
  /** Document title (required). */
  title: string
  /** Author name. */
  author?: string
  /** Date string, e.g. '2026-06-21'. */
  date?: string
  /** Company name (used in report/letter templates). */
  company?: string
  /** Logo image URL (not yet implemented). */
  logo_url?: string
  /** Markdown-formatted body content. */
  content: string
  /** Whether to use two-column layout (article template only). */
  two_column?: boolean
}

/** Response from a PDF generation task submission. */
export interface PDFTaskResponse {
  task_id: string
  status: string
  message: string
}

/** PDF task lifecycle states. */
export type PDFTaskState =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'

/** Detailed status of a PDF generation task. */
export interface PDFTaskStatus {
  id: string
  state: PDFTaskState
  progress: number
  message: string
  template: string
  title: string
  /** Absolute path to the generated PDF file (server-side). */
  file_path?: string | null
  /** Size of the generated PDF in bytes. */
  file_size?: number | null
  created_at?: string | null
  updated_at?: string | null
  error?: string | null
}

/** Paginated list of PDF tasks. */
export interface PDFTaskListResponse {
  items: PDFTaskStatus[]
  total: number
  page: number
  page_size: number
}
