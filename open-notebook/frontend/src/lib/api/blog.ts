/**
 * Blog creation API client.
 *
 * Proxies requests to the open-notebook backend at /api/blog.
 */

import apiClient from './client'
import type {
  BlogExportFormat,
  BlogListResponse,
  BlogPostCreate,
  BlogPostListParams,
  BlogPostResponse,
  BlogPostUpdate,
} from '@/lib/types/blog'

export const blogApi = {
  /**
   * List blog posts (paginated, filterable, searchable).
   */
  listPosts: async (
    params: BlogPostListParams = {}
  ): Promise<BlogListResponse> => {
    const response = await apiClient.get<BlogListResponse>('/blog/posts', {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
        tag: params.tag,
        category: params.category,
        status: params.status,
        search: params.search,
      },
    })
    return response.data
  },

  /**
   * Get a single blog post by ID.
   */
  getPost: async (postId: string): Promise<BlogPostResponse> => {
    const response = await apiClient.get<BlogPostResponse>(
      `/blog/posts/${postId}`
    )
    return response.data
  },

  /**
   * Create a new blog post.
   */
  createPost: async (
    request: BlogPostCreate
  ): Promise<BlogPostResponse> => {
    const response = await apiClient.post<BlogPostResponse>(
      '/blog/posts',
      request
    )
    return response.data
  },

  /**
   * Update an existing blog post. Only provided fields are applied.
   */
  updatePost: async (
    postId: string,
    request: BlogPostUpdate
  ): Promise<BlogPostResponse> => {
    const response = await apiClient.put<BlogPostResponse>(
      `/blog/posts/${postId}`,
      request
    )
    return response.data
  },

  /**
   * Delete a blog post.
   */
  deletePost: async (postId: string): Promise<void> => {
    await apiClient.delete(`/blog/posts/${postId}`)
  },

  /**
   * Publish a blog post (set status to 'published').
   */
  publishPost: async (postId: string): Promise<BlogPostResponse> => {
    const response = await apiClient.post<BlogPostResponse>(
      `/blog/posts/${postId}/publish`
    )
    return response.data
  },

  /**
   * Unpublish a blog post (set status back to 'draft').
   */
  unpublishPost: async (postId: string): Promise<BlogPostResponse> => {
    const response = await apiClient.post<BlogPostResponse>(
      `/blog/posts/${postId}/unpublish`
    )
    return response.data
  },

  /**
   * Export a blog post as Markdown or HTML.
   *
   * Triggers a browser download via a blob URL.
   */
  exportPost: async (
    postId: string,
    format: BlogExportFormat
  ): Promise<void> => {
    const response = await apiClient.get(`/blog/posts/${postId}/export`, {
      params: { format },
      responseType: 'blob',
    })
    // 从 Content-Disposition 头解析文件名，回退到默认名
    const disposition = response.headers['content-disposition'] || ''
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/i)
    const filename = filenameMatch
      ? filenameMatch[1]
      : `blog-post.${format}`

    const blob = new Blob([response.data], { type: response.data.type })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },

  /**
   * List all tags used across blog posts.
   */
  listTags: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/blog/tags')
    return response.data
  },

  /**
   * List all categories used across blog posts.
   */
  listCategories: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/blog/categories')
    return response.data
  },
}
