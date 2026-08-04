// 共享 API 客户端
// 提供笔记本共享链接的创建、访问、撤销和列表接口

import apiClient from './client'

// 权限级别
export type SharePermission = 'READ_ONLY' | 'COMMENT' | 'EDIT'

// 共享链接
export interface ShareLink {
  id: string
  notebook_id: string
  token: string
  permissions: SharePermission
  expires_at?: string | null
  created_by?: string | null
  created: string
  updated: string
}

// 创建共享链接的请求
export interface CreateShareLinkRequest {
  permissions: SharePermission
  expires_at?: string | null
  created_by?: string
}

// 共享笔记本的只读视图响应
export interface SharedNotebook {
  notebook_id: string
  notebook_name: string
  notebook_description: string
  permissions: SharePermission
  sources: Array<{
    id: string
    title?: string | null
    created: string
    updated: string
  }>
  notes: Array<{
    id: string
    title?: string | null
    created: string
    updated: string
  }>
}

export const shareApi = {
  // 创建共享链接
  create: async (notebookId: string, data: CreateShareLinkRequest) => {
    const response = await apiClient.post<ShareLink>(
      `/share/notebook/${notebookId}`,
      data
    )
    return response.data
  },

  // 通过 token 访问共享笔记本
  get: async (token: string) => {
    const response = await apiClient.get<SharedNotebook>(`/share/${token}`)
    return response.data
  },

  // 撤销共享链接
  revoke: async (linkId: string) => {
    const response = await apiClient.delete(`/share/${linkId}`)
    return response.data
  },

  // 列出笔记本的所有共享链接
  list: async (notebookId: string) => {
    const response = await apiClient.get<ShareLink[]>(
      `/share/notebook/${notebookId}/links`
    )
    return response.data
  },
}
