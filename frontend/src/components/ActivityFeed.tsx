export type ActivityItem = {
  title: string
  detail: string
  time: string
  status: 'success' | 'failed'
  initials: string
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return <div className="empty-panel compact-empty"><div className="empty-icon">◷</div><h3>No executions yet</h3><p>Completed workflow runs will show up here.</p></div>
  }
  return (
    <div className="activity-list">
      {items.map((item, index) => (
        <article className="activity-row" key={`${item.title}-${item.time}`}>
          <div className={`activity-avatar activity-color-${index % 3}`}>{item.initials}</div>
          <div className="activity-copy"><h3>{item.title}</h3><p><span className={`run-indicator ${item.status}`} />{item.detail}</p></div>
          <time>{item.time}</time>
        </article>
      ))}
    </div>
  )
}
