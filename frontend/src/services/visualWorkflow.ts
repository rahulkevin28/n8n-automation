import type { Edge } from '@xyflow/react'
import type { Workflow, WorkflowStep } from './api'
import type { WorkflowCanvasNode } from '../components/builder/WorkflowNodes'
import type { SavedWorkflowCanvas } from '../pages/WorkflowBuilder'

export type WorkflowValidation = { workflow?: Workflow; errors: string[] }

const actions: Record<string, readonly string[]> = {
  text: ['uppercase', 'lowercase', 'replace'],
  calculator: ['add', 'subtract', 'multiply', 'divide'],
  json: ['parse', 'get', 'set', 'stringify'],
  condition: ['if'],
}

export function canvasFromWorkflow(workflow: Workflow): SavedWorkflowCanvas {
  const nodes: WorkflowCanvasNode[] = workflow.steps.map((step, index) => {
    const type = step.tool === 'condition' ? 'condition' : step.tool === 'calculator' ? 'calculator' : step.tool === 'json' ? 'json' : 'text'
    const inputs = step.inputs
    return {
      id: step.id, type, position: { x: 160 + index * 250, y: 150 },
      data: {
        label: step.id, action: step.action,
        text: typeof inputs.text === 'string' ? inputs.text : '',
        old: typeof inputs.old === 'string' ? inputs.old : '',
        replacement: typeof inputs.new === 'string' ? inputs.new : '',
        a: typeof inputs.a === 'number' ? inputs.a : 0,
        b: typeof inputs.b === 'number' ? inputs.b : 0,
        value: typeof inputs.value === 'string' ? inputs.value : '',
        path: typeof inputs.path === 'string' ? inputs.path : '',
        newValue: typeof inputs.new_value === 'string' ? inputs.new_value : '',
        operator: typeof inputs.operator === 'string' ? inputs.operator : 'equals',
        target: typeof inputs.target === 'string' ? inputs.target : '',
        maxRetries: typeof step.max_retries === 'number' ? step.max_retries : 0,
        timeoutSeconds: typeof step.timeout_seconds === 'number' ? step.timeout_seconds : 0,
      },
    }
  })
  const hasCondition = nodes.some((node) => node.type === 'condition')
  const edges = hasCondition
    ? workflow.steps.flatMap((step) => [
        step.true_next ? { id: `${step.id}-true`, source: step.id, target: step.true_next, sourceHandle: 'true', targetHandle: 'input', type: 'smoothstep', animated: true } : null,
        step.false_next ? { id: `${step.id}-false`, source: step.id, target: step.false_next, sourceHandle: 'false', targetHandle: 'input', type: 'smoothstep', animated: true } : null,
      ]).filter((edge): edge is NonNullable<typeof edge> => edge !== null)
    : nodes.slice(1).map((node, index) => ({ id: `edge-${index}`, source: nodes[index].id, target: node.id, sourceHandle: 'output', targetHandle: 'input', type: 'smoothstep', animated: true }))
  return { nodes, edges, savedAt: new Date().toISOString() }
}

export function buildWorkflowFromCanvas(
  name: string,
  description: string,
  nodes: WorkflowCanvasNode[],
  edges: Edge[],
): WorkflowValidation {
  const errors: string[] = []
  if (!name.trim()) errors.push('Enter a workflow name before execution.')
  if (!nodes.length) errors.push('Add at least one node before execution.')
  const byId = new Map(nodes.map((node) => [node.id, node]))
  const incoming = new Map<string, Edge[]>()
  const outgoing = new Map<string, Edge[]>()

  for (const edge of edges) {
    const source = byId.get(edge.source)
    const target = byId.get(edge.target)
    if (!source || !target) {
      errors.push(`Connection ${edge.id} refers to a missing node.`)
      continue
    }
    const validSource = source.type === 'condition' ? edge.sourceHandle === 'true' || edge.sourceHandle === 'false' : edge.sourceHandle === 'output'
    if (!validSource || edge.targetHandle !== 'input') {
      errors.push(`Connection from ${source.data.label} to ${target.data.label} uses an unsupported port.`)
    }
    incoming.set(target.id, [...(incoming.get(target.id) ?? []), edge])
    outgoing.set(source.id, [...(outgoing.get(source.id) ?? []), edge])
  }

  for (const node of nodes) {
    if (incoming.get(node.id)?.length && incoming.get(node.id)!.length > 1) {
      errors.push(`${node.data.label} has multiple inputs; only one connection per node is supported.`)
    }
    if (node.type !== 'condition' && outgoing.get(node.id)?.length && outgoing.get(node.id)!.length > 1) {
      errors.push(`${node.data.label} branches to multiple nodes; branching is not supported.`)
    }
    if (!incoming.has(node.id) && !outgoing.has(node.id) && nodes.length > 1) {
      errors.push(`${node.data.label} is disconnected.`)
    }
    if (!actions[node.type ?? ''] || !actions[node.type ?? ''].includes(node.data.action)) {
      errors.push(`${node.data.label} uses an unsupported tool or action.`)
    }
    if (node.type === 'condition') {
      if (!node.data.operator || !['equals', 'not_equals', 'greater_than', 'less_than', 'contains', 'is_empty'].includes(node.data.operator)) errors.push(`${node.data.label} has an invalid comparison.`)
      if (!node.data.value && !incoming.has(node.id)) errors.push(`${node.data.label} needs a value.`)
      if (node.data.operator !== 'is_empty' && !node.data.target) errors.push(`${node.data.label} needs a comparison target.`)
      const branches = outgoing.get(node.id) ?? []
      if (branches.filter((edge) => edge.sourceHandle === 'true').length !== 1 || branches.filter((edge) => edge.sourceHandle === 'false').length !== 1) errors.push(`${node.data.label} requires one TRUE and one FALSE connection.`)
    } else if (node.type === 'text') {
      if (!incoming.has(node.id) && (typeof node.data.text !== 'string' || !node.data.text.trim())) errors.push(`${node.data.label} needs text input.`)
      if (node.data.action === 'replace' && (!node.data.old || typeof node.data.old !== 'string')) errors.push(`${node.data.label} needs text to find.`)
      if (node.data.action === 'replace' && typeof node.data.replacement !== 'string') errors.push(`${node.data.label} needs replacement text.`)
    } else if (node.type === 'calculator') {
      for (const key of ['a', 'b'] as const) {
        const value = node.data[key]
        if (typeof value !== 'number' || !Number.isFinite(value)) errors.push(`${node.data.label} value ${key.toUpperCase()} must be a finite number.`)
      }
      if (node.data.action === 'divide' && node.data.b === 0) errors.push(`${node.data.label} cannot divide by zero.`)
    }
  }

  const roots = nodes.filter((node) => !incoming.has(node.id))
  if (nodes.length > 1 && roots.length !== 1) errors.push('Connections must form one sequential workflow with a single starting node.')
  const ordered: WorkflowCanvasNode[] = nodes.some((node) => node.type === 'condition') ? [...nodes] : []
  const visited = new Set<string>()
  let current: WorkflowCanvasNode | undefined = nodes.some((node) => node.type === 'condition') ? undefined : roots[0]
  while (current && !visited.has(current.id)) {
    ordered.push(current)
    visited.add(current.id)
    const nextEdge: Edge | undefined = outgoing.get(current.id)?.[0]
    current = nextEdge ? byId.get(nextEdge.target) : undefined
  }
  if (!nodes.some((node) => node.type === 'condition') && ordered.length !== nodes.length) errors.push('Connections contain a cycle or do not connect every node in sequence.')

  if (nodes.some((node) => node.type === 'condition')) {
    const visiting = new Set<string>()
    const complete = new Set<string>()
    const visit = (id: string): void => {
      if (visiting.has(id)) { errors.push('Connections contain a cycle.'); return }
      if (complete.has(id)) return
      visiting.add(id)
      for (const edge of outgoing.get(id) ?? []) visit(edge.target)
      visiting.delete(id)
      complete.add(id)
    }
    for (const node of nodes) visit(node.id)
  }

  for (const edge of edges) {
    const source = byId.get(edge.source)
    const target = byId.get(edge.target)
    if (source && target && source.type !== 'condition' && source.type !== target.type) {
      errors.push(`Cannot connect ${source.type} output to ${target.type} input: the tool input types are incompatible.`)
    }
  }

  if (errors.length) return { errors: [...new Set(errors)] }

  const steps: WorkflowStep[] = ordered.map((node) => {
    const prior = incoming.get(node.id)?.[0]
    const inputReference = prior ? { $ref: prior.source } : undefined
    const incomingRef = inputReference
    const inputs: Record<string, unknown> = node.type === 'condition'
      ? { value: incomingRef ?? node.data.value, operator: node.data.operator, ...(node.data.operator !== 'is_empty' ? { target: node.data.target } : {}) }
      : node.type === 'text'
      ? node.data.action === 'replace'
        ? { text: inputReference ?? node.data.text, old: node.data.old, new: node.data.replacement }
        : { text: inputReference ?? node.data.text }
      : node.type === 'json'
        ? node.data.action === 'parse' || node.data.action === 'stringify'
          ? { value: inputReference ?? node.data.value }
          : node.data.action === 'get'
            ? { value: inputReference ?? node.data.value, path: node.data.path }
            : { value: inputReference ?? node.data.value, path: node.data.path, new_value: node.data.newValue }
      : {
          a: inputReference ?? node.data.a,
          b: node.data.b,
        }
    const branches = node.type === 'condition' ? outgoing.get(node.id) ?? [] : []
    return { id: node.id, tool: node.type!, action: node.data.action, inputs, max_retries: node.data.maxRetries ?? 0, timeout_seconds: node.data.timeoutSeconds || null, ...(node.type === 'condition' ? { true_next: branches.find((edge) => edge.sourceHandle === 'true')?.target ?? null, false_next: branches.find((edge) => edge.sourceHandle === 'false')?.target ?? null } : {}) }
  })

  return {
    workflow: { id: crypto.randomUUID(), name: name.trim(), description: description.trim(), steps },
    errors: [],
  }
}
