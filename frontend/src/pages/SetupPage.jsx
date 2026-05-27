import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api.js';

const SERVICES = ['payments', 'auth', 'api-gateway', 'database', 'redis'];
const SIGNALS = ['error_spike', 'latency_spike', 'failed_deployment', 'health_check_failure'];
const ACTIONS = ['jira', 'slack'];

export default function SetupPage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [config, setConfig] = useState({
    services: ['payments', 'auth', 'api-gateway'],
    signals: ['error_spike', 'latency_spike'],
    actions: ['jira', 'slack'],
    thresholds: {
      error_rate: 5,
      latency_ms: 2000,
      deployment_window_minutes: 60,
    },
    slack_channel: '#incidents',
    jira_project_key: 'INC',
  });

  function toggle(field, value) {
    setConfig((current) => ({
      ...current,
      [field]: current[field].includes(value)
        ? current[field].filter((item) => item !== value)
        : [...current[field], value],
    }));
  }

  function updateThreshold(name, value) {
    setConfig((current) => ({
      ...current,
      thresholds: {
        ...current.thresholds,
        [name]: Number(value),
      },
    }));
  }

  async function save() {
    setSaving(true);
    setError('');
    try {
      await api.saveConfig(config);
      await api.seedDemo();
      await api.seedDeploys([
        {
          service: 'payments-api',
          version: 'v2.4.1',
          author: 'devops',
          deployed_at: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
          changes_summary: 'Updated payments SDK to v3.2.0',
        },
      ]);
      await api.seedMemory([
        {
          service: 'payments',
          signal_type: 'error_spike',
          root_cause: 'Failed deploy introduced null pointer in payments module',
          resolution: 'Rollback to previous version',
          duration_minutes: 34,
          occurred_at: '2026-03-03T14:00:00Z',
        },
      ]);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page">
      <section className="setup-layout">
        <p className="eyebrow">SentinelAI</p>
        <h1>Incident agent setup</h1>
        <div className="form-grid">
          <div className="panel">
            <h2>Services</h2>
            {SERVICES.map((service) => (
              <label className="check-row" key={service}>
                <input
                  type="checkbox"
                  checked={config.services.includes(service)}
                  onChange={() => toggle('services', service)}
                />
                {service}
              </label>
            ))}
          </div>

          <div className="panel">
            <h2>Signals</h2>
            {SIGNALS.map((signal) => (
              <label className="check-row" key={signal}>
                <input
                  type="checkbox"
                  checked={config.signals.includes(signal)}
                  onChange={() => toggle('signals', signal)}
                />
                {signal}
              </label>
            ))}
          </div>

          <div className="panel">
            <h2>Actions</h2>
            {ACTIONS.map((action) => (
              <label className="check-row" key={action}>
                <input
                  type="checkbox"
                  checked={config.actions.includes(action)}
                  onChange={() => toggle('actions', action)}
                />
                {action}
              </label>
            ))}
            <label className="field">
              Slack channel
              <input
                value={config.slack_channel}
                onChange={(event) =>
                  setConfig((current) => ({ ...current, slack_channel: event.target.value }))
                }
              />
            </label>
            <label className="field">
              Jira project
              <input
                value={config.jira_project_key}
                onChange={(event) =>
                  setConfig((current) => ({ ...current, jira_project_key: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="panel">
            <h2>Thresholds</h2>
            <label className="field">
              Error rate %
              <input
                type="number"
                value={config.thresholds.error_rate}
                onChange={(event) => updateThreshold('error_rate', event.target.value)}
              />
            </label>
            <label className="field">
              Latency ms
              <input
                type="number"
                value={config.thresholds.latency_ms}
                onChange={(event) => updateThreshold('latency_ms', event.target.value)}
              />
            </label>
            {error && <p className="error-text">{error}</p>}
            <button type="button" disabled={saving} onClick={save}>
              {saving ? 'Preparing demo...' : 'Start monitoring'}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
