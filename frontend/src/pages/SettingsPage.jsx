import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card } from '../components/ui.jsx';

export default function SettingsPage() {
  const [tab, setTab] = useState('integrations');
  const [integrations, setIntegrations] = useState([]);
  const [oncall, setOncall] = useState({ engineer_name: '', slack_handle: '', team: '', start_time: '', end_time: '' });
  const [message, setMessage] = useState('');

  async function load() {
    const data = await api.getIntegrations();
    setIntegrations(data.integrations || []);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function saveIntegration(type, config) {
    await api.saveIntegration({ type, enabled: true, config });
    setMessage(`${type} saved`);
    await load();
  }

  async function saveOncall() {
    await api.createOncall(oncall);
    setMessage('On-call schedule saved');
  }

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <p className="eyebrow">Control plane</p>
          <h1>Settings</h1>
        </div>
      </div>
      {message && <div className="notice">{message}</div>}
      <div className="tabs">
        {['integrations', 'on-call'].map((item) => (
          <button type="button" className={tab === item ? 'active' : 'ghost-button'} onClick={() => setTab(item)} key={item}>
            {item}
          </button>
        ))}
      </div>

      {tab === 'integrations' && (
        <div className="service-grid">
          <IntegrationCard type="slack" saved={integrations.find((item) => item.type === 'slack')} onSave={saveIntegration} />
          <IntegrationCard type="jira" saved={integrations.find((item) => item.type === 'jira')} onSave={saveIntegration} />
          <Card><p className="eyebrow">Coming soon</p><h2>Datadog, Linear, Teams</h2><p className="muted">UI-ready, API wiring later.</p></Card>
        </div>
      )}

      {tab === 'on-call' && (
        <Card>
          <p className="eyebrow">On-call schedule</p>
          <div className="form-grid">
            <input placeholder="Engineer name" value={oncall.engineer_name} onChange={(event) => setOncall({ ...oncall, engineer_name: event.target.value })} />
            <input placeholder="@slack" value={oncall.slack_handle} onChange={(event) => setOncall({ ...oncall, slack_handle: event.target.value })} />
            <input placeholder="team" value={oncall.team} onChange={(event) => setOncall({ ...oncall, team: event.target.value })} />
            <input type="datetime-local" value={oncall.start_time} onChange={(event) => setOncall({ ...oncall, start_time: event.target.value })} />
            <input type="datetime-local" value={oncall.end_time} onChange={(event) => setOncall({ ...oncall, end_time: event.target.value })} />
          </div>
          <button type="button" onClick={saveOncall}>Save on-call</button>
        </Card>
      )}
    </main>
  );
}

function IntegrationCard({ type, saved, onSave }) {
  const [config, setConfig] = useState({});
  const isSlack = type === 'slack';
  return (
    <Card>
      <p className="eyebrow">{saved?.enabled ? 'Connected' : 'Not connected'}</p>
      <h2>{type}</h2>
      <div className="form-grid single">
        {isSlack ? (
          <>
            <input placeholder="webhook_url" onChange={(event) => setConfig({ ...config, webhook_url: event.target.value })} />
            <input placeholder="#channel" onChange={(event) => setConfig({ ...config, channel: event.target.value })} />
          </>
        ) : (
          <>
            <input placeholder="base_url" onChange={(event) => setConfig({ ...config, base_url: event.target.value })} />
            <input placeholder="email" onChange={(event) => setConfig({ ...config, email: event.target.value })} />
            <input placeholder="api_token" type="password" onChange={(event) => setConfig({ ...config, api_token: event.target.value })} />
            <input placeholder="project_key" onChange={(event) => setConfig({ ...config, project_key: event.target.value })} />
          </>
        )}
      </div>
      <button type="button" onClick={() => onSave(type, config)}>Save {type}</button>
    </Card>
  );
}
