import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type NodeTypes,
} from '@xyflow/react'
import { Icon } from '../App'
import { CalculatorWorkflowNode, ConditionWorkflowNode, JsonWorkflowNode, TextWorkflowNode, type WorkflowCanvasNode, type WorkflowNodeData } from '../components/builder/WorkflowNodes'
import { ApiError, createWorkflow, executeApprovedWorkflow, listWorkflows, updateWorkflow, type Workflow, type WorkflowExecutionResult } from '../services/api'
import { buildWorkflowFromCanvas, canvasFromWorkflow } from '../services/visualWorkflow'

export type SavedWorkflowCanvas = {
  nodes: WorkflowCanvasNode[]
  edges: Edge[]
  savedAt: string
}

type WorkflowBuilderProps = {
  savedCanvas: SavedWorkflowCanvas | null
  onSave: (canvas: SavedWorkflowCanvas) => void | Promise<void>
  onExecuted: (workflowId: string) => void
}

const calculatorDefaults: WorkflowNodeData = {
  label: 'Calculator', action: 'add', text: '', old: '', replacement: '', a: 12, b: 8, value: '', path: '', newValue: '', operator: 'equals', target: '',
  maxRetries: 0, timeoutSeconds: 0,
}
const textDefaults: WorkflowNodeData = {
  label: 'Text processing', action: 'uppercase', text: '', old: '', replacement: '', a: 0, b: 0, value: '', path: '', newValue: '', operator: 'equals', target: '',
  maxRetries: 0, timeoutSeconds: 0,
}
const jsonDefaults: WorkflowNodeData = {
  label: 'JSON transform', action: 'parse', text: '', old: '', replacement: '', a: 0, b: 0, value: '{"name":"Ada"}', path: 'name', newValue: '', operator: 'equals', target: '',
  maxRetries: 0, timeoutSeconds: 0,
}
const conditionDefaults: WorkflowNodeData = { label: 'IF condition', action: 'if', text: '', old: '', replacement: '', a: 0, b: 0, value: '', path: '', newValue: '', operator: 'equals', target: '', maxRetries: 0, timeoutSeconds: 0 }
const workflowNodeTypes = { text: TextWorkflowNode, calculator: CalculatorWorkflowNode, json: JsonWorkflowNode, condition: ConditionWorkflowNode }

export function WorkflowBuilder({ savedCanvas, onSave, onExecuted }: WorkflowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowCanvasNode>(savedCanvas?.nodes ?? [])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(savedCanvas?.edges ?? [])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState(savedCanvas?.savedAt ?? '')
  const [notice, setNotice] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saving, setSaving] = useState(false)
  const [workflowName, setWorkflowName] = useState('Visual workflow')
  const [workflowDescription, setWorkflowDescription] = useState('Created in the visual workflow builder')
  const [currentWorkflowId, setCurrentWorkflowId] = useState('')
  const [savedWorkflows, setSavedWorkflows] = useState<Workflow[]>([])
  const [pendingWorkflow, setPendingWorkflow] = useState<Workflow | null>(null)
  const [executionResult, setExecutionResult] = useState<WorkflowExecutionResult | null>(null)
  const [executionError, setExecutionError] = useState('')
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [executionLoading, setExecutionLoading] = useState(false)
  const [approvalChecked, setApprovalChecked] = useState(false)
  const [savedSignature, setSavedSignature] = useState(() => signatureFor(
    savedCanvas?.nodes ?? [],
    savedCanvas?.edges ?? [],
  ))
  const nodeTypes = useMemo(() => workflowNodeTypes as NodeTypes, [])
  const currentSignature = useMemo(() => signatureFor(nodes, edges), [nodes, edges])
  const hasUnsavedChanges = currentSignature !== savedSignature
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null

  useEffect(() => { void listWorkflows().then(setSavedWorkflows).catch(() => setSavedWorkflows([])) }, [])

  const onConnect = useCallback((connection: Connection) => {
    setEdges((current) => addEdge({ ...connection, type: 'smoothstep', animated: true }, current))
    setSelectedEdgeId(null)
    setNotice('')
    setSaveError('')
  }, [setEdges])

  function handleNodesChange(changes: Parameters<typeof onNodesChange>[0]) {
    if (changes.some((change) => change.type === 'position' || change.type === 'remove' || change.type === 'add' || change.type === 'replace')) {
      setNotice('')
      setSaveError('')
    }
    onNodesChange(changes)
  }

  function handleEdgesChange(changes: Parameters<typeof onEdgesChange>[0]) {
    if (changes.some((change) => change.type === 'remove' || change.type === 'add' || change.type === 'replace')) {
      setNotice('')
      setSaveError('')
    }
    onEdgesChange(changes)
  }

  function addNode(type: 'text' | 'calculator' | 'json' | 'condition') {
    const count = nodes.length
    const node: WorkflowCanvasNode = {
      id: `${type}-${crypto.randomUUID()}`,
      type,
      position: { x: 170 + (count % 3) * 55, y: 125 + count * 55 },
      data: { ...(type === 'text' ? textDefaults : type === 'json' ? jsonDefaults : type === 'condition' ? conditionDefaults : calculatorDefaults) },
    }
    setNodes((current) => [...current, node])
    setSelectedNodeId(node.id)
    setSelectedEdgeId(null)
    setNotice('')
    setSaveError('')
  }

  function updateSelectedNode(key: keyof WorkflowNodeData, value: string | number) {
    if (!selectedNodeId) return
    setNotice('')
    setSaveError('')
    setNodes((current) => current.map((node) => node.id === selectedNodeId
      ? { ...node, data: { ...node.data, [key]: value } }
      : node))
  }

  function deleteSelectedNode() {
    if (!selectedNodeId) return
    setNotice('')
    setSaveError('')
    setNodes((current) => current.filter((node) => node.id !== selectedNodeId))
    setEdges((current) => current.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId))
    setSelectedNodeId(null)
  }

  function deleteSelectedEdge() {
    if (!selectedEdgeId) return
    setNotice('')
    setSaveError('')
    setEdges((current) => current.filter((edge) => edge.id !== selectedEdgeId))
    setSelectedEdgeId(null)
  }

  function clearCanvas() {
    setNodes([])
    setEdges([])
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
    setNotice('Canvas cleared. Save to update your local workflow snapshot.')
    setSaveError('')
  }

  async function saveCanvas() {
    if (!hasUnsavedChanges || saving) return
    setSaving(true)
    setSaveError('')
    setNotice('')
    try {
      const validation = buildWorkflowFromCanvas(workflowName, workflowDescription, nodes, edges)
      if (!validation.workflow) {
        setValidationErrors(validation.errors)
        throw new Error('Workflow validation failed')
      }
      const savedWorkflow = currentWorkflowId ? await updateWorkflow({ ...validation.workflow, id: currentWorkflowId }) : await createWorkflow(validation.workflow)
      const snapshot = {
        nodes: serializableNodes(nodes),
        edges: serializableEdges(edges),
        savedAt: new Date().toISOString(),
      }
      await onSave(snapshot)
      setCurrentWorkflowId(savedWorkflow.id)
      setSavedWorkflows((current) => [savedWorkflow, ...current.filter((item) => item.id !== savedWorkflow.id)])
      setSavedSignature(signatureFor(snapshot.nodes, snapshot.edges))
      setSavedAt(snapshot.savedAt)
      setNotice('Workflow saved in this frontend session.')
    } catch {
      setSaveError('Could not save this workflow snapshot. Your canvas is unchanged; please try again.')
    } finally {
      setSaving(false)
    }
  }

  function prepareExecution() {
    const validation = buildWorkflowFromCanvas(workflowName, workflowDescription, nodes, edges)
    setValidationErrors(validation.errors)
    setExecutionError('')
    setExecutionResult(null)
    if (validation.workflow) {
      setPendingWorkflow(validation.workflow)
      setApprovalChecked(false)
    } else {
      setPendingWorkflow(null)
    }
  }

  function openWorkflow(workflow: Workflow) {
    const canvas = canvasFromWorkflow(workflow)
    setNodes(canvas.nodes)
    setEdges(canvas.edges)
    setCurrentWorkflowId(workflow.id)
    setWorkflowName(workflow.name)
    setWorkflowDescription(workflow.description)
    setSavedSignature(signatureFor(canvas.nodes, canvas.edges))
    setSavedAt(canvas.savedAt)
    setNotice(`Loaded ${workflow.name}`)
    setValidationErrors([])
  }

  async function approveAndExecute() {
    if (!pendingWorkflow || !approvalChecked || executionLoading) return
    setExecutionLoading(true)
    setExecutionError('')
    try {
      const result = await executeApprovedWorkflow(pendingWorkflow)
      setExecutionResult(result)
      setPendingWorkflow(null)
      onExecuted(result.workflow_id)
    } catch (cause) {
      setExecutionError(cause instanceof ApiError ? cause.message : 'Workflow execution failed. Please try again.')
    } finally {
      setExecutionLoading(false)
    }
  }

  function cancelApproval() {
    setPendingWorkflow(null)
    setApprovalChecked(false)
  }

  return (
    <section className="builder-page">
      <div className="builder-toolbar">
          <div className="builder-toolbar-copy"><span className="builder-breadcrumb">WORKFLOW DESIGNER</span><strong>{nodes.length} nodes <i /> {edges.length} connections</strong></div>
        <div className="builder-toolbar-actions">
          <button className="builder-secondary-button" onClick={clearCanvas} disabled={!nodes.length && !edges.length}>Clear canvas</button>
          <button className="builder-run-button" onClick={prepareExecution} disabled={executionLoading}><Icon name="play" /> Run workflow</button>
          <button className="builder-save-button" onClick={() => void saveCanvas()} disabled={!hasUnsavedChanges || saving}>
            <Icon name="check" /> {saving ? 'Saving…' : hasUnsavedChanges ? 'Save workflow' : savedAt ? 'Saved' : 'No changes'}
          </button>
        </div>
      </div>

      <div className="builder-workflow-meta">
        <label>Saved workflow<select value={currentWorkflowId} onChange={(event) => { const workflow = savedWorkflows.find((item) => item.id === event.target.value); if (workflow) openWorkflow(workflow) }}><option value="">New workflow</option>{savedWorkflows.map((workflow) => <option value={workflow.id} key={workflow.id}>{workflow.name}</option>)}</select></label>
        <label>Workflow name<input value={workflowName} onChange={(event) => setWorkflowName(event.target.value)} /></label>
        <label>Description<input value={workflowDescription} onChange={(event) => setWorkflowDescription(event.target.value)} /></label>
      </div>

      {validationErrors.length > 0 && <div className="visual-validation-errors" role="alert"><strong>Workflow needs attention</strong><ul>{validationErrors.map((error) => <li key={error}>{error}</li>)}</ul></div>}
      {executionError && <div className="visual-execution-error" role="alert">{executionError}</div>}
      {executionResult && <section className="visual-execution-results" aria-live="polite">
        <div className="visual-results-heading"><div><span>EXECUTION RESULT · {executionResult.execution_id}</span><h2>Workflow {executionResult.status}</h2></div><button onClick={() => setExecutionResult(null)} aria-label="Dismiss execution result">×</button></div>
        <div className="visual-results-steps">{executionResult.steps.map((step, index) => <article className={`execution-step ${step.status}`} key={`${step.id ?? step.step_id}-${index}`}>
          <div className="execution-step-heading"><strong>{step.id ?? step.step_id}</strong><span className={`execution-status ${step.status}`}>{step.status}</span></div>
          {step.output !== null && step.output !== undefined && <pre>{displayOutput(step.output)}</pre>}
          {step.error && <p className="execution-error">{step.error}</p>}
        </article>)}</div>
      </section>}

      <div className="builder-workspace">
        <div className="builder-canvas-wrap">
          <div className="canvas-toolbar">
            <div className="canvas-save-state" role="status"><span className={`canvas-live-dot ${hasUnsavedChanges ? 'unsaved' : 'saved'}`} /> CANVAS <span className="canvas-divider">/</span> <span>{saving ? 'Saving…' : hasUnsavedChanges ? 'Unsaved changes' : savedAt ? 'Saved' : 'No changes yet'}</span></div>
            <div className="add-node-actions">
              <button onClick={() => addNode('text')}><span className="add-node-symbol text">T</span> Text node <b>＋</b></button>
              <button onClick={() => addNode('calculator')}><span className="add-node-symbol calculator">±</span> Calculator <b>＋</b></button>
              <button onClick={() => addNode('json')}><span className="add-node-symbol json">{`{}`}</span> JSON <b>＋</b></button>
              <button onClick={() => addNode('condition')}><span className="add-node-symbol condition">?</span> IF / ELSE <b>＋</b></button>
            </div>
          </div>
          <div className="flow-canvas">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, node) => { setSelectedNodeId(node.id); setSelectedEdgeId(null) }}
              onEdgeClick={(_, edge) => { setSelectedEdgeId(edge.id); setSelectedNodeId(null) }}
              onPaneClick={() => { setSelectedNodeId(null); setSelectedEdgeId(null) }}
              onSelectionChange={({ nodes: selectedNodes, edges: selectedEdges }) => {
                if (!selectedNodes.length && !selectedEdges.length) return
                setSelectedNodeId(selectedNodes[0]?.id ?? null)
                setSelectedEdgeId(selectedEdges[0]?.id ?? null)
              }}
              fitView
              deleteKeyCode={['Backspace', 'Delete']}
              defaultEdgeOptions={{ type: 'smoothstep', animated: true }}
              proOptions={{ hideAttribution: true }}
            >
              <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#373943" />
              <Controls position="bottom-left" showInteractive={false} />
              <MiniMap position="bottom-right" pannable zoomable nodeColor={(node) => node.type === 'calculator' ? '#7c9de8' : '#9a83ed'} maskColor="rgba(12, 13, 17, .72)" />
            </ReactFlow>
            {!nodes.length && <div className="canvas-empty-hint"><span className="canvas-empty-icon"><Icon name="spark" /></span><strong>Your canvas is ready</strong><span>Add a node above, then connect the output to another node.</span><button onClick={() => addNode('text')}>Add your first node <Icon name="arrow" /></button></div>}
          </div>
        </div>

        <aside className="node-inspector">
          <div className="inspector-heading"><div><span>CONFIGURATION</span><h2>{selectedNode ? 'Node settings' : selectedEdge ? 'Connection' : 'Workflow structure'}</h2></div><span className="inspector-sliders">☷</span></div>
          {selectedNode ? <>
            <div className="inspector-node-kind"><span className={`inspector-kind-icon ${selectedNode.type}`}>{selectedNode.type === 'text' ? 'T' : selectedNode.type === 'calculator' ? '±' : '{}'}</span><div><strong>{selectedNode.data.label}</strong><span>{selectedNode.type === 'text' ? 'Text tool' : selectedNode.type === 'calculator' ? 'Calculator tool' : 'JSON tool'}</span></div></div>
            <label className="inspector-label" htmlFor="node-label">Node name</label>
            <input className="inspector-input" id="node-label" value={selectedNode.data.label} onChange={(event) => updateSelectedNode('label', event.target.value)} />
            {selectedNode.type === 'text' ? <TextConfiguration data={selectedNode.data} onChange={updateSelectedNode} /> : selectedNode.type === 'calculator' ? <CalculatorConfiguration data={selectedNode.data} onChange={updateSelectedNode} /> : selectedNode.type === 'json' ? <JsonConfiguration data={selectedNode.data} onChange={updateSelectedNode} /> : <ConditionConfiguration data={selectedNode.data} onChange={updateSelectedNode} />}
            <ExecutionSettings data={selectedNode.data} onChange={updateSelectedNode} />
            <div className="inspector-delete-divider" />
            <button className="delete-selection-button" onClick={deleteSelectedNode}>⌫ <span>Delete node</span></button>
          </> : selectedEdge ? <>
            <div className="connection-card"><span className="connection-glyph">↗</span><strong>Node connection</strong><p>Connects the output of one node to the input of another.</p><small>{selectedEdge.source} <b>→</b> {selectedEdge.target}</small></div>
            <div className="inspector-delete-divider" />
            <button className="delete-selection-button" onClick={deleteSelectedEdge}>⌫ <span>Delete connection</span></button>
          </> : <div className="inspector-empty"><span className="inspector-empty-art"><span /><span /><span /></span><strong>Select a node to configure</strong><p>Choose a node on the canvas to edit its name, action, and inputs.</p><div className="inspector-tip"><b>TIP</b> Drag between node handles to create a connection.</div></div>}
        </aside>
      </div>
      <div className="builder-footer"><span><span className="local-save-dot" /> Backend workflow storage · SQLite</span><span className="builder-save-feedback" role={saveError ? 'alert' : 'status'}>{saveError || notice || (hasUnsavedChanges ? 'Changes are saved when you select Save workflow' : savedAt ? `Saved ${new Date(savedAt).toLocaleString()}` : 'Add or edit nodes to create a saveable workflow')}</span></div>

      {pendingWorkflow && <div className="modal-backdrop" role="presentation"><section className="create-modal builder-approval-modal" role="dialog" aria-modal="true" aria-labelledby="builder-approval-title">
        <div className="modal-top"><div className="modal-icon"><Icon name="play" /></div><button className="modal-close" onClick={cancelApproval} disabled={executionLoading} aria-label="Cancel approval">×</button></div>
        <div className="modal-eyebrow">EXPLICIT APPROVAL REQUIRED</div>
        <h2 id="builder-approval-title">Review before execution</h2>
        <p className="modal-description">This sends the workflow below to the backend executor. It will run only after you check the approval box and confirm.</p>
        <div className="approval-workflow-summary"><strong>{pendingWorkflow.name}</strong><span>{pendingWorkflow.steps.length} sequential steps</span><pre>{JSON.stringify(pendingWorkflow, null, 2)}</pre></div>
        <label className="approval-check"><input type="checkbox" checked={approvalChecked} onChange={(event) => setApprovalChecked(event.target.checked)} disabled={executionLoading} /><span>I reviewed these steps and explicitly approve execution.</span></label>
        <div className="modal-actions"><button className="secondary-button" onClick={cancelApproval} disabled={executionLoading}>Cancel</button><button className="primary-button" onClick={() => void approveAndExecute()} disabled={!approvalChecked || executionLoading}>{executionLoading ? 'Executing…' : 'Approve & execute'} <Icon name="arrow" /></button></div>
      </section></div>}
    </section>
  )
}

function displayOutput(output: unknown): string {
  if (typeof output === 'string') return output
  try { return JSON.stringify(output, null, 2) } catch { return 'Output could not be displayed.' }
}

function serializableNodes(nodes: WorkflowCanvasNode[]): WorkflowCanvasNode[] {
  return nodes.map(({ id, type, position, data }) => ({ id, type, position: { ...position }, data: { ...data } }))
}

function serializableEdges(edges: Edge[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    ...(edge.sourceHandle ? { sourceHandle: edge.sourceHandle } : {}),
    ...(edge.targetHandle ? { targetHandle: edge.targetHandle } : {}),
    ...(edge.type ? { type: edge.type } : {}),
    ...(edge.animated !== undefined ? { animated: edge.animated } : {}),
    ...(edge.label !== undefined ? { label: edge.label } : {}),
    ...(edge.data ? { data: { ...edge.data } } : {}),
    ...(edge.style ? { style: { ...edge.style } } : {}),
  }))
}

function signatureFor(nodes: WorkflowCanvasNode[], edges: Edge[]): string {
  return JSON.stringify({ nodes: serializableNodes(nodes), edges: serializableEdges(edges) })
}

function TextConfiguration({ data, onChange }: { data: WorkflowNodeData; onChange: (key: keyof WorkflowNodeData, value: string | number) => void }) {
  return <>
    <label className="inspector-label" htmlFor="text-action">Action</label>
    <select className="inspector-input" id="text-action" value={data.action} onChange={(event) => onChange('action', event.target.value)}>
      <option value="uppercase">Convert to uppercase</option><option value="lowercase">Convert to lowercase</option><option value="replace">Find and replace</option>
    </select>
    <label className="inspector-label" htmlFor="text-input">Text input</label>
    <textarea className="inspector-input inspector-textarea" id="text-input" value={data.text} onChange={(event) => onChange('text', event.target.value)} placeholder="Enter text to process" rows={4} />
    {data.action === 'replace' && <><label className="inspector-label" htmlFor="text-find">Find</label><input className="inspector-input" id="text-find" value={data.old} onChange={(event) => onChange('old', event.target.value)} /><label className="inspector-label" htmlFor="text-replace">Replace with</label><input className="inspector-input" id="text-replace" value={data.replacement} onChange={(event) => onChange('replacement', event.target.value)} /></>}
    <p className="inspector-help">Inputs are sent to the backend only when you approve execution.</p>
  </>
}

function CalculatorConfiguration({ data, onChange }: { data: WorkflowNodeData; onChange: (key: keyof WorkflowNodeData, value: string | number) => void }) {
  return <>
    <label className="inspector-label" htmlFor="calculator-action">Operation</label>
    <select className="inspector-input" id="calculator-action" value={data.action} onChange={(event) => onChange('action', event.target.value)}>
      <option value="add">Add</option><option value="subtract">Subtract</option><option value="multiply">Multiply</option><option value="divide">Divide</option>
    </select>
    <div className="number-input-row"><div><label className="inspector-label" htmlFor="calculator-a">Value A</label><input className="inspector-input" id="calculator-a" type="number" value={data.a} onChange={(event) => onChange('a', Number(event.target.value))} /></div><div><label className="inspector-label" htmlFor="calculator-b">Value B</label><input className="inspector-input" id="calculator-b" type="number" value={data.b} onChange={(event) => onChange('b', Number(event.target.value))} /></div></div>
    <p className="inspector-help">Values are sent to the backend only when you approve execution.</p>
  </>
}

function JsonConfiguration({ data, onChange }: { data: WorkflowNodeData; onChange: (key: keyof WorkflowNodeData, value: string | number) => void }) {
  return <>
    <label className="inspector-label" htmlFor="json-action">Action</label>
    <select className="inspector-input" id="json-action" value={data.action} onChange={(event) => onChange('action', event.target.value)}><option value="parse">Parse JSON</option><option value="get">Get path</option><option value="set">Set path</option><option value="stringify">Stringify JSON</option></select>
    <label className="inspector-label" htmlFor="json-value">JSON value</label>
    <textarea className="inspector-input inspector-textarea" id="json-value" value={data.value} onChange={(event) => onChange('value', event.target.value)} placeholder='{"name":"Ada"}' rows={3} />
    {(data.action === 'get' || data.action === 'set') && <><label className="inspector-label" htmlFor="json-path">Path</label><input className="inspector-input" id="json-path" value={data.path} onChange={(event) => onChange('path', event.target.value)} placeholder="user.name" /></>}
    {data.action === 'set' && <><label className="inspector-label" htmlFor="json-new-value">New value</label><input className="inspector-input" id="json-new-value" value={data.newValue} onChange={(event) => onChange('newValue', event.target.value)} /></>}
    <p className="inspector-help">Use dotted paths such as user.name. Connected JSON nodes pass the prior output by reference.</p>
  </>
}

function ConditionConfiguration({ data, onChange }: { data: WorkflowNodeData; onChange: (key: keyof WorkflowNodeData, value: string | number) => void }) {
  return <>
    <label className="inspector-label" htmlFor="condition-operator">Comparison</label>
    <select className="inspector-input" id="condition-operator" value={data.operator} onChange={(event) => onChange('operator', event.target.value)}><option value="equals">Equals</option><option value="not_equals">Not equals</option><option value="greater_than">Greater than</option><option value="less_than">Less than</option><option value="contains">Contains</option><option value="is_empty">Is empty</option></select>
    <label className="inspector-label" htmlFor="condition-value">Value</label><input className="inspector-input" id="condition-value" value={data.value} onChange={(event) => onChange('value', event.target.value)} placeholder="Value or prior output" />
    {data.operator !== 'is_empty' && <><label className="inspector-label" htmlFor="condition-target">Target</label><input className="inspector-input" id="condition-target" value={data.target} onChange={(event) => onChange('target', event.target.value)} placeholder="Comparison target" /></>}
    <p className="inspector-help">Connect the TRUE and FALSE handles explicitly to two next steps.</p>
  </>
}

function ExecutionSettings({ data, onChange }: { data: WorkflowNodeData; onChange: (key: keyof WorkflowNodeData, value: string | number) => void }) {
  return <>
    <label className="inspector-label" htmlFor="max-retries">Max retries</label>
    <input className="inspector-input" id="max-retries" type="number" min="0" max="5" value={data.maxRetries ?? 0} onChange={(event) => onChange('maxRetries', Number(event.target.value))} />
    <label className="inspector-label" htmlFor="timeout-seconds">Timeout (seconds)</label>
    <input className="inspector-input" id="timeout-seconds" type="number" min="0" max="3600" step="0.1" value={data.timeoutSeconds ?? 0} onChange={(event) => onChange('timeoutSeconds', Number(event.target.value))} />
    <p className="inspector-help">Zero disables retries or timeout.</p>
  </>
}
