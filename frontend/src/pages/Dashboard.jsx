import { useEffect, useState } from 'react';

import { api } from '../api.js';
import DemoControlBar from '../components/DemoControlBar.jsx';
import DeployFeed from '../components/DeployFeed.jsx';
import IncidentCommandPanel from '../components/IncidentCommandPanel.jsx';
import IncidentHistory from '../components/IncidentHistory.jsx';
import IntegrationStatus from '../components/IntegrationStatus.jsx';
import MetricChart from '../components/MetricChart.jsx';
import MetricsPanel from '../components/MetricsPanel.jsx';
import PostMortemViewer from '../components/PostMortemViewer.jsx';
import RollbackTerminal from '../components/RollbackTerminal.jsx';
import TimelineFeed from '../components/TimelineFeed.jsx';

export default function Dashboard() {
  const [state, setState] = useState(null);
  const [history, setHistory] = useState({});
  const [incidents, setIncidents] = useState({ active: [], resolved: [] });
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [postMortem, setPostMortem] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());

  const incident = selectedIncident || state?.active_incident;

  async function refresh() {
    try {
      const [demoState, metricHistory, incidentList] = await Promise.all([
        api.getDemoState(),
        api.getMetricHistory(180),
        api.getIncidents(),
      ]);
      setState(demoState);
      setHistory(metricHistory.history || {});
      setIncidents(incidentList);
      if (!selectedIncident && demoState.active_incident?.post_mortem) {
        setPostMortem(demoState.active_incident.post_mortem);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 2000);
    return () => window.clearInterval(interval);
  }, [selectedIncident]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
      setSelectedIncident(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function selectHistory(incidentId) {
    const detail = await api.getIncident(incidentId);
    setSelectedIncident(detail);
    setPostMortem(detail.post_mortem || '');
  }

  const countdown = state?.worker?.payment_spike_at
    ? Math.max(0, Math.ceil((new Date(state.worker.payment_spike_at).getTime() - now) / 1000))
    : null;
  const activeTimeline = incident?.timeline || state?.timeline || [];
  const slaWarning = activeTimeline.find((event) => event.event_type === 'sla_warning');
  const correlation = activeTimeline.find((event) => event.event_type === 'correlation_detected');
  const agentStep = activeTimeline.findLast?.((event) =>
    ['detection', 'investigation_completed', 'jira_created', 'slack_sent', 'rollback_completed'].includes(event.event_type),
  );

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Monitoring</p>
          <h1>SentinelAI Dashboard</h1>
        </div>
        <div className={`status-pill ${incident ? 'active' : ''}`}>
          <span className="status-dot" />
          {incident ? `${incident.severity} active` : 'Standing by'}
        </div>
      </header>

      {error && <div className="notice">{error}</div>}
      <section className="panel agent-stepper">
        {['detection', 'investigation_completed', 'jira_created', 'slack_sent', 'rollback_completed'].map((step) => (
          <span className={activeTimeline.some((event) => event.event_type === step) ? 'done' : ''} key={step}>
            {step.replaceAll('_', ' ')}
          </span>
        ))}
        <strong>{countdown ? `Autonomous detection in ${countdown}s` : agentStep ? `Latest: ${agentStep.event_type.replaceAll('_', ' ')}` : 'Agent is watching'}</strong>
      </section>

      <DemoControlBar
        busy={busy}
        countdown={countdown}
        workerState={state?.worker}
        onFullSeed={() => run(() => api.fullSeed())}
        onReset={() => run(() => api.resetDemo(true))}
        onTrigger={() => run(() => api.triggerDemo(30))}
        onInject={() =>
          run(() =>
            api.injectSignal({
              service: 'payments',
              type: 'error_spike',
              value: 18,
              baseline: 0.2,
              unit: 'percent',
            }),
          )
        }
      />

      <div className="dashboard-grid">
        <section className="main-stack">
          <section className="stats-grid">
            <div className="panel stat-card">
              <p className="eyebrow">System score</p>
              <h2>{incident ? '68' : '94'}</h2>
            </div>
            <div className="panel stat-card">
              <p className="eyebrow">Active</p>
              <h2>{incidents.active?.length || 0}</h2>
            </div>
            <div className="panel stat-card">
              <p className="eyebrow">SLA</p>
              <h2>{slaWarning ? 'At risk' : 'Healthy'}</h2>
            </div>
            <div className="panel stat-card">
              <p className="eyebrow">Correlation</p>
              <h2>{correlation ? 'Detected' : 'Clear'}</h2>
            </div>
          </section>
          <MetricChart history={history} deploys={state?.recent_deploys || []} />
          <MetricsPanel metrics={state?.metrics || []} />
          <IncidentCommandPanel
            incident={incident}
            onRefresh={refresh}
            onResolved={(markdown) => setPostMortem(markdown)}
          />
          <PostMortemViewer incident={incident} markdown={postMortem} />
        </section>

        <aside className="right-rail">
          <IntegrationStatus integrations={state?.integrations || {}} />
          <DeployFeed deploys={state?.recent_deploys || []} />
          <RollbackTerminal
            incident={incident}
            busy={busy}
            onRollback={() => incident && run(() => api.rollbackIncident(incident.incident_id, 0))}
          />
          <TimelineFeed timeline={activeTimeline} />
          <IncidentHistory incidents={incidents} onSelect={selectHistory} />
        </aside>
      </div>
    </main>
  );
}
