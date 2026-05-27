import { useEffect, useState } from 'react';

import { api } from '../api.js';
import IncidentPanel from '../components/IncidentPanel.jsx';
import MetricsPanel from '../components/MetricsPanel.jsx';
import PostMortemPanel from '../components/PostMortemPanel.jsx';
import SignalInjector from '../components/SignalInjector.jsx';

export default function Dashboard() {
  const [metrics, setMetrics] = useState([]);
  const [incident, setIncident] = useState(null);
  const [postMortem, setPostMortem] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadMetrics() {
    try {
      const data = await api.getMetrics();
      setMetrics(data.metrics || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadMetrics();
    const interval = window.setInterval(loadMetrics, 5000);
    return () => window.clearInterval(interval);
  }, []);

  async function inject(signal) {
    setLoading(true);
    setError('');
    setPostMortem('');
    try {
      const data = await api.injectSignal(signal);
      if (data.triggered) {
        setIncident(data);
      } else {
        setIncident(null);
        setError(data.reason || 'Signal did not trigger an incident.');
      }
      await loadMetrics();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page dashboard">
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
      <MetricsPanel metrics={metrics} />
      <SignalInjector loading={loading} onInject={inject} />
      {incident && !postMortem && (
        <IncidentPanel incident={incident} onResolved={(data) => setPostMortem(data.post_mortem)} />
      )}
      {postMortem && <PostMortemPanel postMortem={postMortem} />}
    </main>
  );
}
