import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'

export type WorkflowNodeData = {
  label: string
  action: string
  text: string
  old: string
  replacement: string
  a: number
  b: number
  value: string
  path: string
  newValue: string
  operator: string
  target: string
  maxRetries: number
  timeoutSeconds: number
} & Record<string, unknown>

export type WorkflowCanvasNode = Node<WorkflowNodeData, 'text' | 'calculator' | 'json' | 'condition'>

export function TextWorkflowNode({ data, selected }: NodeProps<WorkflowCanvasNode>) {
  return (
    <div className={`builder-node text-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Left} id="input" />
      <div className="builder-node-top"><span className="node-icon text-icon">T</span><span className="node-kind">TEXT TOOL</span><span className="node-menu-dot">···</span></div>
      <strong className="builder-node-title">{data.label || 'Text processing'}</strong>
      <span className="builder-node-action">{data.action === 'replace' ? 'Find and replace' : data.action === 'lowercase' ? 'Convert to lowercase' : 'Convert to uppercase'}</span>
      <div className="builder-node-preview">{data.text || 'Enter text in the settings panel'}</div>
      <div className="node-port-label output-label">OUTPUT <span className="port-dot" /></div>
      <Handle type="source" position={Position.Right} id="output" />
    </div>
  )
}

export function CalculatorWorkflowNode({ data, selected }: NodeProps<WorkflowCanvasNode>) {
  const symbols: Record<string, string> = { add: '+', subtract: '−', multiply: '×', divide: '÷' }
  return (
    <div className={`builder-node calculator-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Left} id="input" />
      <div className="builder-node-top"><span className="node-icon calculator-icon">±</span><span className="node-kind">CALCULATOR</span><span className="node-menu-dot">···</span></div>
      <strong className="builder-node-title">{data.label || 'Calculator'}</strong>
      <span className="builder-node-action">{data.action.charAt(0).toUpperCase() + data.action.slice(1)} values</span>
      <div className="calculator-expression"><span>{data.a}</span><b>{symbols[data.action] ?? '+'}</b><span>{data.b}</span></div>
      <div className="node-port-label output-label">RESULT <span className="port-dot" /></div>
      <Handle type="source" position={Position.Right} id="output" />
    </div>
  )
}

export function JsonWorkflowNode({ data, selected }: NodeProps<WorkflowCanvasNode>) {
  return <div className={`builder-node json-node ${selected ? 'selected' : ''}`}>
    <Handle type="target" position={Position.Left} id="input" />
    <div className="builder-node-top"><span className="node-icon json-icon">{`{}`}</span><span className="node-kind">JSON TOOL</span><span className="node-menu-dot">···</span></div>
    <strong className="builder-node-title">{data.label || 'JSON transform'}</strong>
    <span className="builder-node-action">{data.action.charAt(0).toUpperCase() + data.action.slice(1)} JSON</span>
    <div className="builder-node-preview">{data.path || data.value || 'Configure JSON input'}</div>
    <Handle type="source" position={Position.Right} id="output" />
  </div>
}

export function ConditionWorkflowNode({ data, selected }: NodeProps<WorkflowCanvasNode>) {
  return <div className={`builder-node condition-node ${selected ? 'selected' : ''}`}>
    <Handle type="target" position={Position.Left} id="input" />
    <div className="builder-node-top"><span className="node-icon condition-icon">?</span><span className="node-kind">CONDITION</span><span className="node-menu-dot">···</span></div>
    <strong className="builder-node-title">{data.label || 'IF condition'}</strong>
    <span className="builder-node-action">{data.operator.replace('_', ' ')}</span>
    <div className="builder-node-preview">{data.target || 'Compare value'}</div>
    <span className="branch-label true-label">TRUE</span><span className="branch-label false-label">FALSE</span>
    <Handle type="source" position={Position.Right} id="true" style={{ top: '38%' }} />
    <Handle type="source" position={Position.Right} id="false" style={{ top: '72%' }} />
  </div>
}

