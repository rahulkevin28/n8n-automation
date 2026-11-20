import { Icon } from '../App'

type MetricCardProps = {
  label: string
  value: string
  change: string
  icon: 'layers' | 'play' | 'check'
  tone: 'violet' | 'blue' | 'green'
}

export function MetricCard({ label, value, change, icon, tone }: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span className="metric-label">{label}</span><span className={`metric-icon ${tone}`}><Icon name={icon} /></span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-change"><span className={`change-mark ${tone}`}>{tone === 'green' ? '↗' : '＋'}</span>{change}</div>
      <div className={`metric-accent ${tone}`} />
    </article>
  )
}
