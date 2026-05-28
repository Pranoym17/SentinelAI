import { useEffect, useState } from 'react';

import { api } from '../api.js';
import DeployFeed from '../components/DeployFeed.jsx';
import IncidentCommandPanel from '../components/IncidentCommandPanel.jsx';
import IncidentHistory from '../components/IncidentHistory.jsx';
import IntegrationStatus from '../components/IntegrationStatus.jsx';
import MetricChart from '../components/MetricChart.jsx';
import MetricsPanel from '../components/MetricsPanel.jsx';
import PostMortemViewer from '../components/PostMortemViewer.jsx';
import RollbackTerminal from '../components/RollbackTerminal.jsx';
import TimelineFeed from '../components/TimelineFeed.jsx';
import { MetricCell, Panel, SkeletonRows, StatusBadge } from '../components/ui.jsx';

export default function Dashboard() {
  const [state, setState] = useState(null);
  const [history, setHistory] = useState({});
  const [incidents, setIncidents] = useState({ active: [], resolved: [] });
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [postMortem, setPostMortem] = useState('');
  const [loading, setLoading] = useState(true);
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
    } finally {
      setLoading(false);
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
          <h1>Dashboard</h1>
        </div>
        <StatusBadge status={incident ? incident.severity : 'healthy'} />
      </header>

      {error && <div className="notice">{error}</div>}
      <Panel className="compact">
        <div className="action-row">
        {['detection', 'investigation_completed', 'jira_created', 'slack_sent', 'rollback_completed'].map((step) => (
          <span className={`status-badge ${activeTimeline.some((event) => event.event_type === step) ? 'healthy' : 'neutral'}`} key={step}>
            {step.replaceAll('_', ' ')}
          </span>
        ))}
        <span className="label" style={{ alignSelf: 'center', marginLeft: 'auto' }}>
          {countdown ? `Detection armed: ${countdown}s` : agentStep ? `Latest: ${agentStep.event_type.replaceAll('_', ' ')}` : 'Agent is watching'}
        </span>
        </div>
      </Panel>

      <section className="stats-row">
        <MetricCell label="System health" value={incident ? '68' : '94'} status={incident ? 'warning' : 'healthy'} />
        <MetricCell label="Active" value={incidents.active?.length || 0} status={incident ? 'critical' : 'healthy'} />
        <MetricCell label="MTTR" value="0" unit="m" />
        <MetricCell label="SLA" value={slaWarning ? 'risk' : 'ok'} status={slaWarning ? 'warning' : 'healthy'} />
        <MetricCell label="On-call" value="set" status="healthy" />
      </section>

      <div className="grid-dashboard">
        <aside className="stack">
          {loading ? <Panel><SkeletonRows rows={3} /></Panel> : <MetricsPanel metrics={state?.metrics || []} />}
          {loading ? <Panel><SkeletonRows rows={4} /></Panel> : <DeployFeed deploys={state?.recent_deploys || []} />}
          <IntegrationStatus integrations={state?.integrations || {}} />
        </aside>
        <section className="stack">
          <MetricChart history={history} deploys={state?.recent_deploys || []} />
          <TimelineFeed timeline={activeTimeline} />
          <IncidentCommandPanel
            incident={incident}
            onRefresh={refresh}
            onResolved={(markdown) => setPostMortem(markdown)}
          />
          <PostMortemViewer incident={incident} markdown={postMortem} />
        </section>
      </div>

      <div className="grid-dashboard" style={{ marginTop: 16 }}>
        <section className="stack">
          <RollbackTerminal
            incident={incident}
            busy={busy}
            onRollback={() => incident && run(() => api.rollbackIncident(incident.incident_id, 0))}
          />
        </section>
        <aside className="stack">
          <IncidentHistory incidents={incidents} onSelect={selectHistory} />
        </aside>
      </div>
    </main>
  );
}
