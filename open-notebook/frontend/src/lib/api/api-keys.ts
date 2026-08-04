// API Key 管理 API 客户端
// 提供创建、列出、撤销 API Key 的接口

import apiClient from './client'

// API Key 元数据（不含明文）
export interface ApiKey {
  id: string
  name: string
  permissions: string[]
  created: string
  updated: string
  last_used_at?: string | null
}

// 创建 API Key 的请求
export interface CreateApiKeyRequest {
  name: string
  permissions?: string[]
}

// 创建 API Key 的响应（包含明文，仅此一次）
export interface CreateApiKeyResponse {
  id: string
  name: string
  key: string
  permissions: string[]
  created: string
  message: string
}

export const apiKeysApi = {
  // 创建 API Key（返回明文，仅此一次）
  create: async (data: CreateApiKeyRequest) => {
    const response = await apiClient.post<CreateApiKeyResponse>('/api-keys', data)
    return response.data
  },

  // 列出所有 API Keys（不返回明文）
  list: async () => {
    const response = await apiClient.get<ApiKey[]>('/api-keys')
    return response.data
  },

  // 撤销（删除）API Key
  revoke: async (keyId: string) => {
    const response = await apiClient.delete(`/api-keys/${keyId}`)
    return response.data
  },
}
