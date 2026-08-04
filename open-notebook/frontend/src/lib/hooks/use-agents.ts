/**
 * React Query hooks for the multi-agent system.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { agentsApi } from '@/lib/api/agents'
import type {
  AgentCreateRequest,
  AgentStatus,
  TaskCreateRequest,
  TaskStatus,
} from '@/lib/types/agents'

const QUERY_KEYS = {
  agents: (status?: AgentStatus) => ['agents', 'list', status ?? 'all'] as const,
  tasks: (status?: TaskStatus) => ['agents', 'tasks', status ?? 'all'] as const,
  stats: ['agents', 'stats'] as const,
  messages: (agentId?: string) =>
    ['agents', 'messages', agentId ?? 'all'] as const,
}

export function useAgents(status?: AgentStatus) {
  return useQuery({
    queryKey: QUERY_KEYS.agents(status),
    queryFn: () => agentsApi.listAgents(status),
    refetchInterval: 3_000, // Poll for status updates
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: AgentCreateRequest) => agentsApi.createAgent(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (agentId: string) => agentsApi.deleteAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useSetupDefaultAgents() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => agentsApi.setupDefaults(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useTasks(status?: TaskStatus) {
  return useQuery({
    queryKey: QUERY_KEYS.tasks(status),
    queryFn: () => agentsApi.listTasks(status),
    refetchInterval: 2_000, // Poll for task progress
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: TaskCreateRequest) => agentsApi.createTask(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'tasks'] })
    },
  })
}

export function useCancelTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => agentsApi.cancelTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'tasks'] })
    },
  })
}

export function useAgentStats() {
  return useQuery({
    queryKey: QUERY_KEYS.stats,
    queryFn: () => agentsApi.getStats(),
    refetchInterval: 3_000,
  })
}

export function useAgentMessages(agentId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.messages(agentId),
    queryFn: () => agentsApi.getMessages(agentId),
    refetchInterval: 5_000,
  })
}

export function useSendMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      fromAgent,
      toAgent,
      content,
    }: {
      fromAgent: string
      toAgent: string
      content: string
    }) => agentsApi.sendMessage(fromAgent, toAgent, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'messages'] })
    },
  })
}
