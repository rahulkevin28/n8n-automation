import { useState, type FormEvent } from 'react'
import { ApiError, executeWorkflow, planWorkflow, type Workflow, type WorkflowExecutionResult } from '../services/api'
import { Icon } from '../App'

type CreateWorkflowModalProps = {
  onClose: () => void
  onExecuted: (workflow: Workflow, result: WorkflowExecutionResult) => void
}

type ModalStage = 'describe' | 'review' | 'result'

export function CreateWorkflowModal({ onClose, onExecuted }: CreateWorkflowModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [result, setResult] = useState<WorkflowExecutionResult | null>(null)
  const [stage, setStage] = useState<ModalStage>('describe')
  const [approved, setApproved] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handlePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim() || !description.trim()) {
      setError('Add a workflow name and task description to continue.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const planned = await planWorkflow(description.trim())
      const reviewedWorkflow = { ...planned, name: planned.name?.trim() || name.trim() }
      setWorkflow(reviewedWorkflow)
      setApproved(false)
      setStage('review')
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'The workflow plan could not be created. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApproveAndRun() {
    if (!workflow || !approved) return
    setLoading(true)
    setError('')
    try {
      const execution = await executeWorkflow(workflow)
      setResult(execution)
      setStage('result')
      onExecuted(workflow, execution)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'The workflow could not be executed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !loading) onClose() }}>
      <section className="create-modal integration-modal" role="dialog" aria-modal="true" aria-labelledby="create-title">
        <div className="modal-top"><div className="modal-icon"><Icon name="spark" /></div><button className="modal-close" onClick={onClose} aria-label="Close dialog" disabled={loading}>×</button></div>

        {stage === 'describe' && <>
          <div className="modal-eyebrow">NEW AUTOMATION</div>
          <h2 id="create-title">Create a workflow</h2>
          <p className="modal-description">Describe a task and Gemini will draft a workflow for you to review before anything runs.</p>
          <form onSubmit={handlePlan}>
            <label htmlFor="workflow-name">Workflow name</label>
            <input id="workflow-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Daily support summary" autoFocus disabled={loading} />
            <label htmlFor="workflow-task">Task description</label>
            <textarea id="workflow-task" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the task you want to automate…" rows={4} disabled={loading} />
            <div className="form-note"><Icon name="info" /><span>Planning creates a proposal only. It will not run until you review and approve it.</span></div>
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose} disabled={loading}>Cancel</button><button type="submit" className="primary-button" disabled={loading}>{loading ? 'Creating plan…' : 'Generate plan'} {!loading && <Icon name="arrow" />}</button></div>
          </form>
        </>}

        {stage === 'review' && workflow && <>
          <div className="modal-eyebrow">REVIEW BEFORE RUNNING</div>
          <h2 id="create-title">{workflow.name}</h2>
          <p className="modal-description">{workflow.description}</p>
          <div className="review-id">Workflow ID <code>{workflow.id}</code></div>
          <div className="review-steps" aria-label="Proposed workflow steps">
            {workflow.steps.length === 0 ? <p className="review-empty">This plan has no steps to run.</p> : workflow.steps.map((step, index) => (
              <article className="review-step" key={`${step.id}-${index}`}>
                <span className="review-step-number">{String(index + 1).padStart(2, '0')}</span>
                <div className="review-step-body">
                  <strong>{step.id}</strong>
                  <span><b>{step.tool}</b><i>.</i>{step.action}</span>
                  <pre>{JSON.stringify(step.inputs, null, 2)}</pre>
                </div>
              </article>
            ))}
          </div>
          <label className="approval-check"><input type="checkbox" checked={approved} onChange={(event) => setApproved(event.target.checked)} disabled={loading} /><span>I reviewed this workflow and approve its execution.</span></label>
          <div className="approval-note"><Icon name="info" /><span>Only registered tools and actions can run. This action will execute the workflow and save its run history.</span></div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => { setStage('describe'); setError(''); setApproved(false) }} disabled={loading}>Back</button><button type="button" className="primary-button" onClick={handleApproveAndRun} disabled={!approved || loading}>{loading ? 'Running workflow…' : 'Approve & run'} {!loading && <Icon name="arrow" />}</button></div>
        </>}

        {stage === 'result' && result && <>
          <div className="modal-eyebrow">EXECUTION COMPLETE · {result.execution_id}</div>
          <h2 id="create-title">Workflow {result.status}</h2>
          <p className="modal-description">Run ID <code>{result.execution_id}</code> · Workflow <code>{result.workflow_id}</code></p>
          <div className="execution-steps">
            {result.steps.map((step, index) => (
              <article className={`execution-step ${step.status}`} key={`${step.id ?? step.step_id}-${index}`}>
                <div className="execution-step-heading"><strong>{step.id ?? step.step_id}</strong><span className={`execution-status ${step.status}`}>{step.status}</span></div>
                {step.output !== null && step.output !== undefined && <pre>{formatOutput(step.output)}</pre>}
                {step.error && <p className="execution-error">{step.error}</p>}
              </article>
            ))}
          </div>
          <div className="modal-actions"><button type="button" className="primary-button" onClick={onClose}>Done <Icon name="check" /></button></div>
        </>}
      </section>
    </div>
  )
}

function formatOutput(output: unknown): string {
  if (typeof output === 'string') return output
  try { return JSON.stringify(output, null, 2) } catch { return 'Output could not be displayed.' }
}
