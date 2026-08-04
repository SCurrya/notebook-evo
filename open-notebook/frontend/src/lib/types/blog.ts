/**
 * Blog creation types.
 *
 * Integrates with the open-notebook backend at /api/blog.
 */

/** 博客文章状态：草稿或已发布 */
export type BlogPostStatus = 'draft' | 'published'

/** 导出格式：Markdown 或 HTML */
export type BlogExportFormat = 'md' | 'html'

/** 创建博客文章的请求体 */
export interface BlogPostCreate {
  title: string
  content?: string
  tags?: string[]
  category?: string
  author?: string
}

/** 更新博客文章的请求体（所有字段可选） */
export interface BlogPostUpdate {
  title?: string
  content?: string
  tags?: string[]
  category?: string
  author?: string
  status?: BlogPostStatus
}

/** 单篇博客文章的响应 */
export interface BlogPostResponse {
  id: string
  title: string
  content: string
  html: string
  tags: string[]
  category: string | null
  status: BlogPostStatus
  author: string | null
  created_at: string
  updated_at: string
}

/** 博客文章列表查询参数 */
export interface BlogPostListParams {
  page?: number
  page_size?: number
  tag?: string
  category?: string
  status?: BlogPostStatus
  search?: string
}

/** 分页博客文章列表响应 */
export interface BlogListResponse {
  items: BlogPostResponse[]
  total: number
  page: number
  page_size: number
}

/** 兼容别名：完整文章对象 */
export type BlogPost = BlogPostResponse
