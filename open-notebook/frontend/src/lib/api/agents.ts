/**
 * Multi-Agent API client.
 */

import apiClient from './client'
import type {
  Agent,
  AgentCreateRequest,
  AgentMessage,
  AgentStats,
  AgentStatus,
  Task,
  TaskCreateRequest,
  TaskStatus,
} from '@/lib/types/agents'

export const agentsApi = {
  // Agents
  listAgents: async (status?: AgentStatus): Promise<Agent[]> => {
    const response = await apiClient.get<Agent[]>('/agents', {
      params: status ? { status } : undefined,
    })
    return response.data
  },

  createAgent: async (request: AgentCreateRequest): Promise<Agent> => {
    const response = await apiClient.post<Agent>('/agents', request)
    return response.data
  },

  getAgent: async (agentId: string): Promise<Agent> => {
    const response = await apiClient.get<Agent>(`/agents/${agentId}`)
    return response.data
  },

  deleteAgent: async (agentId: string): Promise<void> => {
    await apiClient.delete(`/agents/${agentId}`)
  },

  setupDefaults: async (): Promise<{
    created_agent_ids: string[]
    scheduler_running: boolean
    total_agents: number
  }> => {
    const response = await apiClient.post('/agents/setup-defaults')
    return response.data
  },

  // Tasks
  listTasks: async (status?: TaskStatus): Promise<Task[]> => {
    const response = await apiClient.get<Task[]>('/agents/tasks', {
      params: status ? { status } : undefined,
    })
    return response.data
  },

  createTask: async (request: TaskCreateRequest): Promise<Task> => {
    const response = await apiClient.post<Task>('/agents/tasks', request)
    return response.data
  },

  getTask: async (taskId: string): Promise<Task> => {
    const response = await apiClient.get<Task>(`/agents/tasks/${taskId}`)
    return response.data
  },

  cancelTask: async (taskId: string): Promise<Task> => {
    const response = await apiClient.post<Task>(
      `/agents/tasks/${taskId}/cancel`
    )
    return response.data
  },

  // Messages
  getMessages: async (
    agentId?: string,
    unreadOnly?: boolean
  ): Promise<AgentMessage[]> => {
    const response = await apiClient.get<AgentMessage[]>('/agents/messages', {
      params: {
        agent_id: agentId,
        unread_only: unreadOnly,
      },
    })
    return response.data
  },

  sendMessage: async (
    fromAgent: string,
    toAgent: string,
    content: string
  ): Promise<AgentMessage> => {
    const response = await apiClient.post<AgentMessage>(
      '/agents/messages',
      null,
      {
        params: { from_agent: fromAgent, to_agent: toAgent, content },
      }
    )
    return response.data
  },

  // Scheduler
  startScheduler: async (): Promise<{ running: boolean }> => {
    const response = await apiClient.post('/agents/scheduler/start')
    return response.data
  },

  stopScheduler: async (): Promise<{ running: boolean }> => {
    const response = await apiClient.post('/agents/scheduler/stop')
    return response.data
  },

  // Stats
  getStats: async (): Promise<AgentStats> => {
    const response = await apiClient.get<AgentStats>('/agents/stats')
    return response.data
  },
}
