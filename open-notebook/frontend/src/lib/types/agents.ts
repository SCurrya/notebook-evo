/**
 * Multi-Agent system types.
 */

export type AgentType =
  | 'generic'
  | 'test'
  | 'build'
  | 'research'
  | 'code'
  | 'review'

export type AgentStatus = 'idle' | 'busy' | 'offline' | 'error'

export type TaskStatus =
  | 'pending'
  | 'assigned'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type TaskPriority = 1 | 2 | 3 | 4

export interface Agent {
  id: string
  name: string
  type: AgentType
  status: AgentStatus
  capabilities: string[]
  current_task_id: string | null
  created_at: string
  last_active: string | null
  metadata: Record<string, unknown>
}

export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  required_capabilities: string[]
  assigned_agent_id: string | null
  dependencies: string[]
  payload: Record<string, unknown>
  result: Record<string, unknown> | null
  error: string | null
  progress: number
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AgentMessage {
  id: string
  from_agent: string
  to_agent: string
  content: string
  timestamp: string
  read: boolean
}

export interface AgentCreateRequest {
  name: string
  type: AgentType
  capabilities: string[]
  metadata?: Record<string, unknown>
}

export interface TaskCreateRequest {
  title: string
  description?: string
  priority?: TaskPriority
  required_capabilities?: string[]
  dependencies?: string[]
  payload?: Record<string, unknown>
}

export interface AgentStats {
  agents: {
    total: number
    idle: number
    busy: number
    offline: number
    error: number
  }
  tasks: {
    total: number
    pending: number
    running: number
    completed: number
    failed: number
  }
  messages: number
}
