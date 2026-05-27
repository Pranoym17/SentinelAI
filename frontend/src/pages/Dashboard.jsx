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

      <DemoControlBar
        busy={busy}
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
          <TimelineFeed timeline={incident?.timeline || state?.timeline || []} />
          <IncidentHistory incidents={incidents} onSelect={selectHistory} />
        </aside>
      </div>
    </main>
  );
}
