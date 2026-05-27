export default function Dashboard() {
  return (
    <main className="page dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">Monitoring</p>
          <h1>SentinelAI Dashboard</h1>
        </div>
        <div className="status-pill">
          <span className="status-dot" />
          Standing by
        </div>
      </header>

      <section className="panel">
        <h2>System shell ready</h2>
        <p className="muted">
          Metrics, signal injection, investigation, Jira, Slack, and post-mortems will be
          added feature by feature.
        </p>
      </section>
    </main>
  );
}
