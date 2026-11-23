import { useState, type FormEvent } from 'react'
import { ApiError, getExecution, getWorkflowExecutions, type ExecutionDetail, type ExecutionSummary } from '../services/api'
import { Icon } from '../App'

export function ExecutionHistory({ knownWorkflowIds }: { knownWorkflowIds: string[] }) {
  const [workflowId, setWorkflowId] = useState(knownWorkflowIds[0] ?? '')
  const [executions, setExecutions] = useState<ExecutionSummary[]>([])
  const [selected, setSelected] = useState<ExecutionDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')
  const [searched, setSearched] = useState(false)

  async function loadHistory(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    const id = workflowId.trim()
    if (!id) {
      setError('Enter a workflow ID to look up its execution history.')
      return
    }
    setLoading(true)
    setError('')
    setSelected(null)
    setDetailError('')
    setSearched(true)
    try {
      const history = await getWorkflowExecutions(id)
      setExecutions(history.executions)
    } catch (cause) {
      setExecutions([])
      setError(cause instanceof ApiError ? cause.message : 'Execution history could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  async function openExecution(executionId: string) {
    setDetailLoading(true)
    setDetailError('')
    setSelected(null)
    try {
      setSelected(await getExecution(executionId))
    } catch (cause) {
      setDetailError(cause instanceof ApiError ? cause.message : 'Execution details could not be loaded.')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <section className="history-panel panel">
      <div className="history-intro"><div><div className="section-kicker">PERSISTED RUNS</div><h2>Execution history</h2><p>History is available by workflow ID. The backend does not currently provide a global workflow list.</p></div><span className="history-api-tag">API CONNECTED</span></div>
      <form className="history-search" onSubmit={loadHistory}>
        <label htmlFor="history-workflow-id">Workflow ID</label>
        <div className="history-search-row">
          <input id="history-workflow-id" value={workflowId} onChange={(event) => setWorkflowId(event.target.value)} placeholder="Paste a workflow ID" list="known-workflow-ids" />
          <datalist id="known-workflow-ids">{knownWorkflowIds.map((id) => <option value={id} key={id} />)}</datalist>
          <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Loading…' : 'Load history'} <Icon name="arrow" /></button>
        </div>
      </form>
      {error && <p className="history-error" role="alert">{error}</p>}
      {loading && <div className="history-state">Loading execution history…</div>}
      {!loading && searched && !error && executions.length === 0 && <div className="history-state"><div className="empty-icon"><Icon name="layers" /></div><strong>No executions yet</strong><span>No saved runs were found for this workflow.</span></div>}
      {!loading && !searched && <div className="history-state"><div className="empty-icon"><Icon name="info" /></div><strong>Look up a workflow</strong><span>Enter an ID or choose one from a workflow executed in this session.</span></div>}
      {!loading && executions.length > 0 && <div className="history-results">
        <div className="execution-list">
          <div className="history-list-label">{executions.length} {executions.length === 1 ? 'EXECUTION' : 'EXECUTIONS'}</div>
          {executions.map((execution) => <button className={`execution-history-row ${selected?.execution_id === execution.execution_id ? 'selected' : ''}`} key={execution.execution_id} onClick={() => void openExecution(execution.execution_id)}>
            <span className={`history-status-dot ${execution.status}`} />
            <span className="execution-history-info"><strong>{execution.status === 'success' ? 'Completed successfully' : 'Run failed'}</strong><small>{formatTime(execution.created_at)}</small></span>
            <code>{execution.execution_id.slice(0, 8)}…</code>
          </button>)}
        </div>
        <div className="execution-detail">
          {detailLoading && <div className="history-state">Loading run details…</div>}
          {detailError && <p className="history-error" role="alert">{detailError}</p>}
          {!selected && !detailLoading && !detailError && <div className="history-state detail-placeholder"><span>Select a run to inspect its steps.</span></div>}
          {selected && <>
            <div className="detail-heading"><div><span>EXECUTION</span><h3>{selected.status === 'success' ? 'Successful run' : 'Run failed'}</h3></div><code>{selected.execution_id}</code></div>
            <div className="detail-steps">{selected.steps.map((step, index) => <article className={`execution-step ${step.status}`} key={`${step.step_id ?? step.id}-${index}`}>
              <div className="execution-step-heading"><strong>{step.step_id ?? step.id}</strong><span className={`execution-status ${step.status}`}>{step.status}</span></div>
              {step.output !== null && step.output !== undefined && <pre>{formatOutput(step.output)}</pre>}
              {step.error && <p className="execution-error">{step.error}</p>}
              {step.attempts !== undefined && step.status !== 'skipped' && <small>{step.attempts} {step.attempts === 1 ? 'attempt' : 'attempts'}</small>}
            </article>)}</div>
          </>}
        </div>
      </div>}
    </section>
  )
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatOutput(value: unknown): string {
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return 'Output could not be displayed.' }
}
