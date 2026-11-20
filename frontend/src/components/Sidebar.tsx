import { Icon } from '../App'

export type NavigationItem = 'Dashboard' | 'Workflows' | 'Visual Builder' | 'Execution History' | 'Settings'

const navigation: { label: NavigationItem; icon: 'grid' | 'workflow' | 'builder' | 'history' | 'settings' }[] = [
  { label: 'Dashboard', icon: 'grid' },
  { label: 'Workflows', icon: 'workflow' },
  { label: 'Visual Builder', icon: 'builder' },
  { label: 'Execution History', icon: 'history' },
  { label: 'Settings', icon: 'settings' },
]

export function Sidebar({ activeItem, onNavigate }: { activeItem: NavigationItem; onNavigate: (item: NavigationItem) => void }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="#dashboard" onClick={(event) => { event.preventDefault(); onNavigate('Dashboard') }}>
        <span className="brand-mark"><span /><span /><span /></span>
        <span className="brand-name">flowforge<span>AI</span></span>
      </a>

      <div className="workspace-switcher">
        <div className="workspace-avatar">N</div>
        <div className="workspace-label"><strong>Northstar Studio</strong><span>Free workspace</span></div>
        <span className="switcher-chevron">⌄</span>
      </div>

      <div className="nav-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {navigation.map((item) => (
          <button key={item.label} className={`nav-item ${activeItem === item.label ? 'active' : ''}`} onClick={() => onNavigate(item.label)} aria-current={activeItem === item.label ? 'page' : undefined}>
            <NavIcon name={item.icon} />
            <span>{item.label}</span>
            {item.label === 'Workflows' && <span className="nav-count">demo</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="usage-card">
          <div className="usage-top"><span>Sample usage</span><span>68%</span></div>
          <div className="usage-track"><span /></div>
          <p>1,284 <span>of 2,000 runs used</span></p>
          <button onClick={() => onNavigate('Settings')}>View plan <span>↗</span></button>
        </div>
        <button className="profile-row">
          <span className="profile-avatar">AR</span><span className="profile-copy"><strong>Alex Rivera</strong><span>Workspace owner</span></span><span className="profile-dots">···</span>
        </button>
      </div>
    </aside>
  )
}

function NavIcon({ name }: { name: 'grid' | 'workflow' | 'builder' | 'history' | 'settings' }) {
  if (name === 'settings') return <Icon name="settings" />
  const content = {
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    workflow: <><rect x="3.5" y="4" width="6" height="5" rx="1.5" /><rect x="14.5" y="15" width="6" height="5" rx="1.5" /><path d="M9.5 6.5h3a2 2 0 0 1 2 2v6.5m0 0-2.5-2.5M14.5 15l2.5-2.5" /></>,
    builder: <><rect x="3.5" y="4" width="6" height="5" rx="1.5" /><rect x="14.5" y="4" width="6" height="5" rx="1.5" /><rect x="9" y="15" width="6" height="5" rx="1.5" /><path d="M6.5 9v3h11V9m-5.5 3v3" /></>,
    history: <><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8" /><path d="M3 3v5h5m4-1v5l3 2" /></>,
    settings: <></>,
  }[name]
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{content}</svg>
}
