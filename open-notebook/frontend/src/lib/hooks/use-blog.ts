/**
 * React Query hooks for blog creation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { blogApi } from '@/lib/api/blog'
import type {
  BlogExportFormat,
  BlogPostCreate,
  BlogPostListParams,
  BlogPostUpdate,
  BlogPostStatus,
} from '@/lib/types/blog'

const QUERY_KEYS = {
  posts: (params: BlogPostListParams) =>
    [
      'blog',
      'posts',
      params.page ?? 1,
      params.page_size ?? 20,
      params.tag,
      params.category,
      params.status,
      params.search,
    ] as const,
  post: (postId: string) => ['blog', 'post', postId] as const,
  tags: ['blog', 'tags'] as const,
  categories: ['blog', 'categories'] as const,
}

/**
 * List blog posts (paginated, filterable, searchable).
 */
export function useBlogPosts(params: BlogPostListParams = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.posts(params),
    queryFn: () => blogApi.listPosts(params),
  })
}

/**
 * Get a single blog post by ID.
 */
export function useBlogPost(postId: string | null) {
  return useQuery({
    queryKey: postId ? QUERY_KEYS.post(postId) : ['blog', 'post', 'none'],
    queryFn: () => blogApi.getPost(postId!),
    enabled: !!postId,
  })
}

/**
 * Create a new blog post.
 */
export function useCreateBlogPost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: BlogPostCreate) => blogApi.createPost(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blog', 'posts'] })
      queryClient.invalidateQueries({ queryKey: ['blog', 'tags'] })
      queryClient.invalidateQueries({ queryKey: ['blog', 'categories'] })
    },
  })
}

/**
 * Update an existing blog post.
 */
export function useUpdateBlogPost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      postId,
      request,
    }: {
      postId: string
      request: BlogPostUpdate
    }) => blogApi.updatePost(postId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['blog', 'posts'] })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.post(data.id),
      })
      queryClient.invalidateQueries({ queryKey: ['blog', 'tags'] })
      queryClient.invalidateQueries({ queryKey: ['blog', 'categories'] })
    },
  })
}

/**
 * Delete a blog post.
 */
export function useDeleteBlogPost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (postId: string) => blogApi.deletePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blog', 'posts'] })
      queryClient.invalidateQueries({ queryKey: ['blog', 'tags'] })
      queryClient.invalidateQueries({ queryKey: ['blog', 'categories'] })
    },
  })
}

/**
 * Publish or unpublish a blog post.
 *
 * 传入 `status` 决定发布或取消发布。
 */
export function usePublishBlogPost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      postId,
      status,
    }: {
      postId: string
      status: BlogPostStatus
    }) =>
      status === 'published'
        ? blogApi.publishPost(postId)
        : blogApi.unpublishPost(postId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['blog', 'posts'] })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.post(data.id),
      })
    },
  })
}

/**
 * Export a blog post as Markdown or HTML (triggers a download).
 */
export function useExportBlogPost() {
  return useMutation({
    mutationFn: ({
      postId,
      format,
    }: {
      postId: string
      format: BlogExportFormat
    }) => blogApi.exportPost(postId, format),
  })
}

/**
 * List all tags used across blog posts.
 */
export function useBlogTags() {
  return useQuery({
    queryKey: QUERY_KEYS.tags,
    queryFn: () => blogApi.listTags(),
    staleTime: 60_000, // 1 minute
  })
}

/**
 * List all categories used across blog posts.
 */
export function useBlogCategories() {
  return useQuery({
    queryKey: QUERY_KEYS.categories,
    queryFn: () => blogApi.listCategories(),
    staleTime: 60_000, // 1 minute
  })
}
