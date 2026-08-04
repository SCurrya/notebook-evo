// 知识图谱 API 客户端
// 提供知识图谱实体和关系的 CRUD 接口

import apiClient from './client'

// 知识图谱实体类型
export interface GraphEntity {
  id: string
  name: string
  type: string
  properties: Record<string, unknown>
  notebook_id?: string | null
}

// 知识图谱关系类型
export interface GraphRelation {
  id: string
  source_id: string
  target_id: string
  type: string
  properties: Record<string, unknown>
}

// 知识图谱响应（包含实体和关系）
export interface GraphData {
  entities: GraphEntity[]
  relations: GraphRelation[]
}

// 创建实体的请求
export interface CreateEntityRequest {
  name: string
  type: string
  properties?: Record<string, unknown>
  notebook_id?: string
}

// 创建关系的请求
export interface CreateRelationRequest {
  source_id: string
  target_id: string
  type: string
  properties?: Record<string, unknown>
}

// 提取知识图谱的请求
export interface ExtractGraphRequest {
  notebook_id: string
}

export const knowledgeGraphApi = {
  // 从笔记本内容提取实体和关系（调用 LLM）
  extract: async (data: ExtractGraphRequest) => {
    const response = await apiClient.post<GraphData>(
      '/knowledge-graph/extract',
      data
    )
    return response.data
  },

  // 获取笔记本的知识图谱
  get: async (notebookId: string) => {
    const response = await apiClient.get<GraphData>(
      `/knowledge-graph/${notebookId}`
    )
    return response.data
  },

  // 手动添加实体
  createEntity: async (data: CreateEntityRequest) => {
    const response = await apiClient.post<GraphEntity>(
      '/knowledge-graph/entity',
      data
    )
    return response.data
  },

  // 手动添加关系
  createRelation: async (data: CreateRelationRequest) => {
    const response = await apiClient.post<GraphRelation>(
      '/knowledge-graph/relation',
      data
    )
    return response.data
  },

  // 删除实体
  deleteEntity: async (entityId: string) => {
    const response = await apiClient.delete(
      `/knowledge-graph/entity/${entityId}`
    )
    return response.data
  },

  // 删除关系
  deleteRelation: async (relationId: string) => {
    const response = await apiClient.delete(
      `/knowledge-graph/relation/${relationId}`
    )
    return response.data
  },
}
