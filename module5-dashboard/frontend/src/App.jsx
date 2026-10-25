import { useState } from 'react'
import './App.css'

const initialApplications = [
  { id: 'APP-2026-001', institution: 'Demo Engineering College', type: 'Extension of Approval', documents: '12/12', status: 'Verified', date: '24 Oct 2026' },
  { id: 'APP-2026-002', institution: 'Sample Technical Institute', type: 'New Programme', documents: '8/10', status: 'Needs Review', date: '24 Oct 2026' },
  { id: 'APP-2026-003', institution: 'Demo Polytechnic College', type: 'Intake Change', documents: '6/9', status: 'Pending', date: '23 Oct 2026' },
  { id: 'APP-2026-004', institution: 'Sample Technology College', type: 'Extension of Approval', documents: '9/10', status: 'Needs Review', date: '23 Oct 2026' },
]

const initialAlerts = [
  { id: 1, level: 'High', title: 'Missing supporting document', detail: 'APP-2026-002 · Required document not uploaded', resolved: false },
  { id: 2, level: 'Medium', title: 'Institution details mismatch', detail: 'APP-2026-004 · Verify the submitted institution details', resolved: false },
  { id: 3, level: 'Medium', title: 'Issuer verification pending', detail: 'APP-2026-003 · Official source response awaited', resolved: false },
]

const initialAudit = [
  { time: '10:42 AM', action: 'Document checklist reviewed', app: 'APP-2026-001', user: 'Demo System' },
  { time: '10:30 AM', action: 'Missing document alert generated', app: 'APP-2026-002', user: 'Demo System' },
  { time: '10:15 AM', action: 'Issuer verification marked pending', app: 'APP-2026-003', user: 'Demo System' },
]

function App() {
  const [applications, setApplications] = useState([
  {
    id: "DEMO-AICTE-001",
    institution: "Demo Engineering College",
    applicationType: "EoA",
    status: "Pending",
    submittedAt: "25 Oct 2026",
    documents: 1,
    isDemo: true,
  },
  ]);
  const [alerts, setAlerts] = useState([])
  const [activeTab, setActiveTab] = useState('Overview')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [audit, setAudit] = useState([])

  const openAlerts = alerts.filter(alert => !alert.resolved).length
  const verified = applications.filter(app => app.status === 'Verified').length
  const needsReview = applications.filter(app => app.status === 'Needs Review').length
  const pending = applications.filter(app => app.status === 'Pending').length

  const filteredApplications = applications.filter(app => {
    const matchesSearch = `${app.id} ${app.institution} ${app.type}`.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'All' || app.status === filter
    return matchesSearch && matchesFilter
  })

  function resolveAlert(alert) {
    if (alert.resolved) return
    setAlerts(current => current.map(item =>
      item.id === alert.id ? { ...item, resolved: true } : item
    ))
    setAudit(current => [{
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      action: `Alert marked reviewed: ${alert.title}`,
      app: alert.detail.split(' · ')[0],
      user: 'Demo Reviewer',
    }, ...current])
  }

  const navItems = [
    { name: 'Overview', icon: '▦' },
    { name: 'Applications', icon: '▤' },
    { name: 'Alerts', icon: '⚑' },
    { name: 'Audit Trail', icon: '◷' },
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">A</div>
          <div><strong>AICTE Verify</strong><small>DOCUMENT INTELLIGENCE</small></div>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navItems.map(item => (
            <button key={item.name}
              className={`nav-item ${activeTab === item.name ? 'active' : ''}`}
              onClick={() => setActiveTab(item.name)}>
              <span className="nav-icon">{item.icon}</span>
              <span>{item.name}</span>
              {item.name === 'Alerts' && openAlerts > 0 && <span className="nav-count">{openAlerts}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="demo-indicator"><span /> SYNTHETIC DEMO DATA</div>
          <div className="profile">
            <div className="avatar">DR</div>
            <div><strong>Demo Reviewer</strong><small>Review workspace</small></div>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">Workspace <span>/</span> {activeTab}</div>
          <div className="topbar-right"><span className="secure-label">♧ Secure review workspace</span><div className="avatar small">DR</div></div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">MODULE 05 · REVIEW & MONITORING</div>
              <h1>{activeTab === 'Overview' ? 'Validation Dashboard' : activeTab}</h1>
              <p>Monitor application validation, unresolved alerts and review activity.</p>
            </div>
            <div className="date-chip">◷ &nbsp; 24 October 2026</div>
          </div>

          <div className="demo-banner">
            <span className="banner-icon">ⓘ</span>
            <div><strong>Prototype demonstration</strong><p>All institutions, application records and activity shown here are synthetic sample data, not official AICTE records.</p></div>
          </div>

          {activeTab === 'Overview' && (
            <>
              <section className="stats-grid">
                <StatCard label="Total Applications" value={applications.length} note="Sample records" icon="▤" color="blue" />
                <StatCard label="Verified" value={verified} note="Checklist passed in demo" icon="✓" color="green" />
                <StatCard label="Needs Review" value={needsReview} note="Requires human review" icon="⚑" color="orange" />
                <StatCard label="Pending" value={pending} note="Awaiting further checks" icon="◷" color="purple" />
              </section>

              <section className="content-grid">
                <div className="panel applications-panel">
                  <div className="panel-heading"><div><h2>Recent Applications</h2><p>Application-wise validation status</p></div><button className="text-button" onClick={() => setActiveTab('Applications')}>View all →</button></div>
                  <ApplicationTable applications={applications.slice(0, 4)} onSelect={app => { setSearch(app.id); setActiveTab('Applications') }} />
                </div>

                <div className="panel alerts-panel">
                  <div className="panel-heading"><div><h2>Open Alerts</h2><p>Items requiring attention</p></div><span className="pill pill-red">{openAlerts} open</span></div>
                  <AlertList alerts={alerts.filter(alert => !alert.resolved).slice(0, 3)} onResolve={resolveAlert} />
                  <button className="outline-button full-button" onClick={() => setActiveTab('Alerts')}>Review all alerts</button>
                </div>
              </section>

              <section className="panel audit-panel">
                <div className="panel-heading"><div><h2>Recent Audit Activity</h2><p>Traceable demo events and review actions</p></div><button className="text-button" onClick={() => setActiveTab('Audit Trail')}>View audit trail →</button></div>
                <AuditList audit={audit.slice(0, 3)} />
              </section>
            </>
          )}

          {activeTab === 'Applications' && (
            <section className="panel">
              <div className="panel-heading"><div><h2>Application Register</h2><p>Search and filter synthetic application records.</p></div></div>
              <div className="table-controls">
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search ID, institution or type..." />
                <select value={filter} onChange={e => setFilter(e.target.value)}>
                  <option>All</option><option>Verified</option><option>Needs Review</option><option>Pending</option>
                </select>
              </div>
              <ApplicationTable applications={filteredApplications} />
              {filteredApplications.length === 0 && <p className="empty-state">No matching demo applications found.</p>}
            </section>
          )}

          {activeTab === 'Alerts' && (
            <section className="panel">
              <div className="panel-heading"><div><h2>Validation Alerts</h2><p>Flags are preliminary indicators, not proof of forgery or non-compliance.</p></div><span className="pill pill-red">{openAlerts} open</span></div>
              <AlertList alerts={alerts} onResolve={resolveAlert} showResolved />
            </section>
          )}

          {activeTab === 'Audit Trail' && (
            <section className="panel">
              <div className="panel-heading"><div><h2>Audit Trail</h2><p>Demo log of system events and reviewer actions.</p></div><span className="pill pill-blue">{audit.length} events</span></div>
              <AuditList audit={audit} />
              <p className="audit-note">Prototype note: this audit trail is stored in page state and resets on refresh. A production system should save audit events in the backend database with access controls and tamper-resistant logging.</p>
            </section>
          )}

          <footer>AICTE Document Verification Prototype <span>•</span> Module 5: Dashboard, Alerts & Audit Trail</footer>
        </div>
      </main>
    </div>
  )
}

function StatCard({ label, value, note, icon, color }) {
  return <div className="stat-card"><div className={`stat-icon ${color}`}>{icon}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>
}

function StatusBadge({ status }) {
  const cls = status === 'Verified' ? 'status-green' : status === 'Pending' ? 'status-purple' : 'status-orange'
  return <span className={`status-badge ${cls}`}><span />{status}</span>
}

function ApplicationTable({ applications, onSelect }) {
  return (
    <div className="table-wrap"><table><thead><tr><th>APPLICATION</th><th>INSTITUTION</th><th>DOCUMENTS</th><th>STATUS</th></tr></thead>
      <tbody>{applications.map(app => <tr key={app.id} onClick={() => onSelect?.(app)} className={onSelect ? 'clickable-row' : ''}>
        <td><strong>{app.id}</strong><small>{app.type}</small></td><td>{app.institution}</td><td>{app.documents}</td><td><StatusBadge status={app.status} /></td>
      </tr>)}</tbody></table></div>
  )
}

function AlertList({ alerts, onResolve, showResolved = false }) {
  if (!alerts.length) return <p className="empty-state">No open alerts. Great work!</p>
  return <div className="alert-list">{alerts.map(alert => (
    <div className={`alert-item ${alert.resolved ? 'resolved' : ''}`} key={alert.id}>
      <div className={`alert-symbol ${alert.level === 'High' ? 'high' : 'medium'}`}>{alert.level === 'High' ? '!' : '⚑'}</div>
      <div className="alert-copy"><div className="alert-title">{alert.title}<span className={`severity ${alert.level.toLowerCase()}`}>{alert.level}</span></div><p>{alert.detail}</p>{alert.resolved && <small className="resolved-label">Marked reviewed</small>}</div>
      {!alert.resolved && <button className="review-button" onClick={() => onResolve(alert)}>Mark reviewed</button>}
      {alert.resolved && showResolved && <span className="reviewed-check">✓ Reviewed</span>}
    </div>
  ))}</div>
}

function AuditList({ audit }) {
  return <div className="audit-list">{audit.map((item, index) => <div className="audit-row" key={`${item.time}-${index}`}><div className="audit-dot">{index === 0 ? '✓' : '•'}</div><div className="audit-copy"><strong>{item.action}</strong><p>{item.app} · By {item.user}</p></div><time>{item.time}</time></div>)}</div>
}

export default App
