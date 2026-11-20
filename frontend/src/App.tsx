import { useEffect, useState } from 'react'
import { ActivityFeed } from './components/ActivityFeed'
import { CreateWorkflowModal } from './components/CreateWorkflowModal'
import { ExecutionHistory } from './components/ExecutionHistory'
import { MetricCard } from './components/MetricCard'
import { Sidebar, type NavigationItem } from './components/Sidebar'
import { WorkflowBuilder, type SavedWorkflowCanvas } from './pages/WorkflowBuilder'
import { WorkflowList } from './components/WorkflowList'
import { AuthScreen } from './components/AuthScreen'
import { ApiError, getCurrentUser, getDashboardStats, setAccessToken, type DashboardStats, type Workflow, type WorkflowExecutionResult } from './services/api'
import './App.css'


const pageTitles: Record<NavigationItem, { title: string; subtitle: string }> = {
  Dashboard: { title: 'Good morning, Alex', subtitle: 'Here’s what’s happening with your workflows today.' },
  Workflows: { title: 'Workflows', subtitle: 'Create, organize, and monitor your automation workflows.' },
  'Visual Builder': { title: 'Visual workflow builder', subtitle: 'Design a workflow by arranging and connecting tool nodes.' },
  'Execution History': { title: 'Execution history', subtitle: 'Review recent workflow runs and their outcomes.' },
  Settings: { title: 'Settings', subtitle: 'Manage your workspace preferences.' },
}

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  useEffect(() => { void getCurrentUser().then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)) }, [])
  const [activePage, setActivePage] = useState<NavigationItem>('Dashboard')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [knownWorkflowIds, setKnownWorkflowIds] = useState<string[]>([])
  const [savedCanvas, setSavedCanvas] = useState<SavedWorkflowCanvas | null>(null)
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null)
  const [dashboardError, setDashboardError] = useState('')
  const [dashboardLoading, setDashboardLoading] = useState(true)
  const [dashboardRefresh, setDashboardRefresh] = useState(0)
  useEffect(() => { if (activePage !== 'Dashboard') return; void getDashboardStats().then((data) => { setDashboard(data); setDashboardError('') }).catch((error) => setDashboardError(error instanceof ApiError ? error.message : 'Dashboard data could not be loaded.')).finally(() => setDashboardLoading(false)) }, [activePage, dashboardRefresh])
  const page = pageTitles[activePage]

  function recordExecution(workflow: Workflow, _result: WorkflowExecutionResult) {
    const workflowId = _result.workflow_id || workflow.id
    setKnownWorkflowIds((current) => [workflowId, ...current.filter((id) => id !== workflowId)])
    setDashboardRefresh((value) => value + 1)
  }

  if (authenticated === null) return <main className="auth-screen"><p>Loading workspace…</p></main>
  if (!authenticated) return <AuthScreen onAuthenticated={() => setAuthenticated(true)} />

  return (
    <div className="app-shell">
      <Sidebar activeItem={activePage} onNavigate={setActivePage} />
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-divider">/</span><strong>{activePage}</strong></div>
          <div className="topbar-actions">
            <span className="workspace-pill"><span className="online-dot" /> All systems operational</span>
            <button className="avatar-button" aria-label="Log out" onClick={() => { setAccessToken(null); setAuthenticated(false) }}>Log out</button>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> WORKSPACE OVERVIEW</div>
              <h1>{page.title}<span className="heading-period">.</span></h1>
              <p className="page-subtitle">{page.subtitle}</p>
            </div>
            {activePage !== 'Visual Builder' && <button className="primary-button" onClick={() => setIsCreateOpen(true)}>
              <Icon name="plus" /> Create workflow
            </button>}
          </section>

          {activePage === 'Dashboard' && dashboardError && <div className="sample-note"><Icon name="info" /><span>{dashboardError}</span></div>}

          {activePage === 'Settings' ? (
            <section className="empty-panel settings-panel">
              <div className="empty-icon"><Icon name="settings" /></div>
              <h2>Workspace settings</h2>
              <p>Settings will be available when workspace preferences are connected.</p>
              <span className="local-tag">Preview</span>
            </section>
          ) : activePage === 'Execution History' ? (
            <ExecutionHistory knownWorkflowIds={knownWorkflowIds} />
          ) : activePage === 'Visual Builder' ? (
            <WorkflowBuilder
              savedCanvas={savedCanvas}
              onSave={setSavedCanvas}
              onExecuted={(workflowId) => setKnownWorkflowIds((current) => [workflowId, ...current.filter((id) => id !== workflowId)])}
            />
          ) : (
            <>
              <section className="metrics-grid" aria-label="Workflow metrics">
                <MetricCard label="Total workflows" value={dashboardLoading ? '…' : String(dashboard?.total_workflows ?? 0)} change="Saved workflows" icon="layers" tone="violet" />
                <MetricCard label="Total executions" value={dashboardLoading ? '…' : String(dashboard?.total_executions ?? 0)} change={`${dashboard?.failed_executions ?? 0} failed`} icon="play" tone="blue" />
                <MetricCard label="Successful runs" value={dashboardLoading ? '…' : String(dashboard?.successful_executions ?? 0)} change={`${dashboard?.success_rate ?? 0}% success rate`} icon="check" tone="green" />
              </section>

              <div className="content-grid">
                <section className="panel workflow-panel">
                  <div className="panel-heading">
                    <div><div className="section-kicker">YOUR AUTOMATIONS</div><h2>Recent workflows</h2></div>
                    <button className="text-button" onClick={() => setActivePage('Workflows')}>View all <Icon name="arrow" /></button>
                  </div>
                  <WorkflowList workflows={(dashboard?.recent_workflows ?? []).map((item) => ({ id: item.workflow_id, name: item.name, description: item.description, status: 'Active', updated: new Date(item.created_at).toLocaleString(), color: 'violet' }))} />
                </section>
                <section className="panel activity-panel">
                  <div className="panel-heading">
                    <div><div className="section-kicker">SAMPLE FEED <span className="pulse-dot" /></div><h2>Recent activity</h2></div>
                    <button className="icon-button" aria-label="More activity options"><Icon name="more" /></button>
                  </div>
                  <ActivityFeed items={(dashboard?.recent_executions ?? []).map((item) => ({ title: item.workflow_id, detail: item.status === 'success' ? 'Completed successfully' : 'Execution failed', time: new Date(item.created_at).toLocaleString(), status: item.status, initials: item.workflow_id.slice(0, 2).toUpperCase() }))} />
                  <button className="activity-footer" onClick={() => setActivePage('Execution History')}>See connected execution history <Icon name="arrow" /></button>
                </section>
              </div>
              <div className="bottom-callout"><div className="callout-mark"><Icon name="spark" /></div><div><strong>Start with a simple idea.</strong><span>Describe a task and FlowForge will help shape it into a workflow.</span></div><button className="callout-link" onClick={() => setIsCreateOpen(true)}>Create your first step <Icon name="arrow" /></button></div>
            </>
          )}
          <footer className="page-footer"><span>FLOWFORGE AI <span className="footer-version">PREVIEW</span></span><span>Built for thoughtful automation <span className="footer-heart">✳</span></span></footer>
        </div>
      </main>
      {isCreateOpen && <CreateWorkflowModal onClose={() => setIsCreateOpen(false)} onExecuted={recordExecution} />}
    </div>
  )
}

export function Icon({ name }: { name: 'plus' | 'info' | 'layers' | 'play' | 'check' | 'arrow' | 'more' | 'spark' | 'settings' }) {
  const paths: Record<typeof name, React.ReactNode> = {
    plus: <path d="M12 5v14M5 12h14" />,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    play: <path d="m8 5 11 7-11 7V5Z" />,
    check: <path d="m5 12 4 4L19 6" />,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
    spark: <><path d="m12 3 1.8 6.2L20 11l-6.2 1.8L12 19l-1.8-6.2L4 11l6.2-1.8L12 3Z" /><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a8 8 0 0 0 0-6l1.4-1.1-1.4-2.4-1.7.6a8 8 0 0 0-5.7-1.7L11.7 2H9l-.3 2.4A8 8 0 0 0 6.3 6l-2-.6L3 7.8 4.5 9a8 8 0 0 0 0 6L3 16.2l1.4 2.4 2-.6a8 8 0 0 0 2.4 1.6L9 22h2.7l.3-2.4a8 8 0 0 0 5.7-1.7l1.7.6 1.4-2.4-1.4-1.1Z" transform="translate(0 0) scale(.92) translate(1 1)" /></>,
  }
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

export default App
