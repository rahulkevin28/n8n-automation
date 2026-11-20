import { Icon } from '../App'

export type WorkflowItem = {
  id: string
  name: string
  description: string
  status: 'Active' | 'Draft'
  updated: string
  color: 'violet' | 'blue' | 'amber'
}

export function WorkflowList({ workflows }: { workflows: WorkflowItem[] }) {
  if (workflows.length === 0) {
    return <div className="empty-panel compact-empty"><div className="empty-icon"><Icon name="layers" /></div><h3>No workflows yet</h3><p>Create a workflow to see it here.</p></div>
  }
  return (
    <div className="workflow-list">
      {workflows.map((workflow, index) => (
        <article className="workflow-row" key={workflow.id}>
          <div className={`workflow-symbol ${workflow.color}`}><span>{workflow.name.slice(0, 1).toUpperCase()}</span><i>{index === 0 ? '✦' : index === 1 ? '↗' : '◌'}</i></div>
          <div className="workflow-copy"><div className="workflow-title-line"><h3>{workflow.name}</h3><span className={`status-pill ${workflow.status.toLowerCase()}`}><span />{workflow.status}</span></div><p>{workflow.description}</p></div>
          <div className="workflow-meta"><span>{workflow.id}</span><small>Edited {workflow.updated}</small></div>
          <button className="row-menu" aria-label={`Options for ${workflow.name}`}><Icon name="more" /></button>
        </article>
      ))}
    </div>
  )
}
