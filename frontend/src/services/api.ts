export type WorkflowStep = {
  id: string
  tool: string
  action: string
  inputs: Record<string, unknown>
  true_next?: string | null
  false_next?: string | null
  max_retries?: number
  timeout_seconds?: number | null
}

export type Workflow = {
  id: string
  name: string
  description: string
  steps: WorkflowStep[]
}

export type PlanWorkflowRequest = { task_description: string }
export type ExecuteWorkflowRequest = { workflow: Workflow; approved: true }

export type ExecutionStepResult = {
  id?: string
  step_id?: string
  status: 'success' | 'failed' | 'skipped'
  output: unknown
  error: string | null
  attempts?: number
}

export type WorkflowExecutionResult = {
  execution_id: string
  workflow_id: string
  status: 'success' | 'failed'
  steps: ExecutionStepResult[]
}

export function executeApprovedWorkflow(workflow: Workflow): Promise<WorkflowExecutionResult> {
  return executeWorkflow(workflow)
}

export function listWorkflows(): Promise<Workflow[]> { return request<Workflow[]>('/workflows') }
export function createWorkflow(workflow: Workflow): Promise<Workflow> { return request<Workflow>('/workflows', { method: 'POST', body: JSON.stringify(workflow) }) }
export function updateWorkflow(workflow: Workflow): Promise<Workflow> { return request<Workflow>(`/workflows/${encodeURIComponent(workflow.id)}`, { method: 'PUT', body: JSON.stringify(workflow) }) }
export function getWorkflow(workflowId: string): Promise<Workflow> { return request<Workflow>(`/workflows/${encodeURIComponent(workflowId)}`) }

export type ExecutionSummary = {
  execution_id: string
  workflow_id: string
  status: 'success' | 'failed'
  created_at: string
}

export type WorkflowExecutionHistory = {
  workflow_id: string
  executions: ExecutionSummary[]
}

export type ExecutionDetail = ExecutionSummary & {
  steps: ExecutionStepResult[]
}
export type DashboardStats = {
  total_workflows: number
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
  recent_workflows: { workflow_id: string; name: string; description: string; created_at: string }[]
  recent_executions: ExecutionSummary[]
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
let accessToken = localStorage.getItem('flowforge_token')
export function setAccessToken(token: string | null) { accessToken = token; if (token) localStorage.setItem('flowforge_token', token); else localStorage.removeItem('flowforge_token') }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    })
  } catch {
    throw new ApiError('Could not reach FlowForge AI. Check that the backend is running and try again.', 0)
  }

  if (!response.ok) {
    const message = response.status === 401
      ? 'Your email or password is incorrect, or your session has expired.'
      : response.status === 409
        ? 'An account with that email already exists.'
        : response.status === 400 || response.status === 422
      ? 'The workflow request could not be validated. Review the workflow and try again.'
      : response.status === 403
        ? 'Execution requires your explicit approval.'
        : response.status === 404
          ? 'No execution history was found for that workflow ID.'
          : response.status === 502 || response.status === 503
            ? 'The workflow service is temporarily unavailable. Please try again shortly.'
            : 'FlowForge AI could not complete the request. Please try again.'
    throw new ApiError(message, response.status)
  }

  try {
    return await response.json() as T
  } catch {
    throw new ApiError('FlowForge AI returned an unreadable response. Please try again.', response.status)
  }
}
export function register(email: string, password: string) { return request<{ access_token: string }>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }) }
export function login(email: string, password: string) { return request<{ access_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }) }
export function getCurrentUser() { return request<{ id: string; email: string; created_at: string }>('/auth/me') }

export function planWorkflow(taskDescription: string): Promise<Workflow> {
  return request<Workflow>('/workflows/plan', {
    method: 'POST',
    body: JSON.stringify({ task_description: taskDescription } satisfies PlanWorkflowRequest),
  })
}

export function executeWorkflow(workflow: Workflow): Promise<WorkflowExecutionResult> {
  return request<WorkflowExecutionResult>('/workflows/execute', {
    method: 'POST',
    body: JSON.stringify({ workflow, approved: true } satisfies ExecuteWorkflowRequest),
  })
}

export function getWorkflowExecutions(workflowId: string): Promise<WorkflowExecutionHistory> {
  return request<WorkflowExecutionHistory>(`/workflows/${encodeURIComponent(workflowId)}/executions`)
}

export function getExecution(executionId: string): Promise<ExecutionDetail> {
  return request<ExecutionDetail>(`/executions/${encodeURIComponent(executionId)}`)
}
export function getDashboardStats(): Promise<DashboardStats> { return request<DashboardStats>('/dashboard/stats') }
