import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { Button, EmptyState, Panel, SectionHeader, StatusBadge } from '../components/ui.jsx';

const integrationTypes = [
  { type: 'slack', title: 'Slack', fields: ['webhook_url', 'channel'], testable: true },
  { type: 'jira', title: 'Jira', fields: ['base_url', 'email', 'api_token', 'project_key', 'issue_type'], testable: true },
  { type: 'github', title: 'GitHub', fields: ['token', 'repo'], testable: true },
  { type: 'datadog', title: 'Datadog', fields: ['api_key', 'app_key'], comingSoon: true },
  { type: 'teams', title: 'Teams', fields: ['webhook_url'], comingSoon: true },
  { type: 'linear', title: 'Linear', fields: ['api_key'], comingSoon: true },
  { type: 'discord', title: 'Discord', fields: ['webhook_url'], comingSoon: true },
];

export default function SettingsPage() {
  const [tab, setTab] = useState('integrations');
  const [integrations, setIntegrations] = useState([]);
  const [services, setServices] = useState([]);
  const [oncall, setOncall] = useState({ engineer_name: '', slack_handle: '', team: '', start_time: '', end_time: '' });
  const [serviceDraft, setServiceDraft] = useState({ name: '', display_name: '', team: '', sla_target: 99.9 });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const integrationMap = useMemo(() => Object.fromEntries(integrations.map((item) => [item.type, item])), [integrations]);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [integrationData, serviceData] = await Promise.all([api.getIntegrations(), api.getServices()]);
      setIntegrations(integrationData.integrations || []);
      setServices(serviceData.services || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function saveIntegration(type, config) {
    setError('');
    try {
      await api.saveIntegration({ type, enabled: true, config });
      setMessage(`${type} saved`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function testIntegration(type) {
    setError('');
    try {
      const result = await api.testIntegration(type);
      setMessage(`${type} test: ${result.ok || result.posted || result.created ? 'passed' : result.reason || 'completed'}`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveOncall() {
    setError('');
    try {
      await api.createOncall(oncall);
      setMessage('On-call schedule saved');
    } catch (err) {
      setError(err.message);
    }
  }

  async function createService() {
    if (!serviceDraft.name) return;
    setError('');
    try {
      await api.createService(serviceDraft);
      setServiceDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
      setMessage('Service created');
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
        </div>
      </div>
      {message && <div className="notice success">{message}</div>}
      {error && <div className="notice">{error}</div>}
      <div className="tabs">
        {['integrations', 'services', 'on-call'].map((item) => (
          <button type="button" className={tab === item ? 'active' : ''} onClick={() => setTab(item)} key={item}>
            {item}
          </button>
        ))}
      </div>

      {loading && <Panel><EmptyState title="Loading settings" copy="Fetching integrations and services." /></Panel>}

      {tab === 'integrations' && !loading && (
        <div className="card-grid three">
          {integrationTypes.map((item) => (
            <IntegrationCard
              key={item.type}
              item={item}
              saved={integrationMap[item.type]}
              onSave={saveIntegration}
              onTest={testIntegration}
            />
          ))}
        </div>
      )}

      {tab === 'services' && !loading && (
        <>
          <div className="card-grid three">
            {services.length === 0 && <Panel><EmptyState title="No services" copy="Create a monitored service below." /></Panel>}
            {services.map((service) => (
              <Panel key={service.id}>
                <span className="label">{service.team || 'No team'}</span>
                <h2>{service.display_name || service.name}</h2>
                <p className="muted">{service.sla_target}% SLA target</p>
              </Panel>
            ))}
          </div>
          <Panel>
            <SectionHeader title="Add service" />
            <div className="form-grid">
              <input placeholder="name" value={serviceDraft.name} onChange={(event) => setServiceDraft({ ...serviceDraft, name: event.target.value })} />
              <input placeholder="display name" value={serviceDraft.display_name} onChange={(event) => setServiceDraft({ ...serviceDraft, display_name: event.target.value })} />
              <input placeholder="team" value={serviceDraft.team} onChange={(event) => setServiceDraft({ ...serviceDraft, team: event.target.value })} />
              <input type="number" value={serviceDraft.sla_target} onChange={(event) => setServiceDraft({ ...serviceDraft, sla_target: Number(event.target.value) })} />
            </div>
            <Button onClick={createService}>Create service</Button>
          </Panel>
        </>
      )}

      {tab === 'on-call' && !loading && (
        <Panel>
          <SectionHeader title="On-call schedule" />
          <div className="form-grid">
            <input placeholder="Engineer name" value={oncall.engineer_name} onChange={(event) => setOncall({ ...oncall, engineer_name: event.target.value })} />
            <input placeholder="@slack" value={oncall.slack_handle} onChange={(event) => setOncall({ ...oncall, slack_handle: event.target.value })} />
            <input placeholder="team" value={oncall.team} onChange={(event) => setOncall({ ...oncall, team: event.target.value })} />
            <input type="datetime-local" value={oncall.start_time} onChange={(event) => setOncall({ ...oncall, start_time: event.target.value })} />
            <input type="datetime-local" value={oncall.end_time} onChange={(event) => setOncall({ ...oncall, end_time: event.target.value })} />
          </div>
          <Button disabled={!oncall.engineer_name} onClick={saveOncall}>Save on-call</Button>
        </Panel>
      )}
    </main>
  );
}

function IntegrationCard({ item, saved, onSave, onTest }) {
  const [config, setConfig] = useState(saved?.config || {});
  useEffect(() => {
    setConfig(saved?.config || {});
  }, [saved?.id]);

  return (
    <Panel>
      <div className="service-card-head">
        <StatusBadge status={item.comingSoon ? 'neutral' : saved?.enabled ? 'healthy' : 'critical'} />
      </div>
      <h2>{item.title}</h2>
      <div className="form-grid single">
        {item.fields.map((field) => (
          <input
            key={field}
            placeholder={field}
            type={field.includes('token') || field.includes('key') ? 'password' : 'text'}
            value={config[field] || ''}
            disabled={item.comingSoon}
            onChange={(event) => setConfig({ ...config, [field]: event.target.value })}
          />
        ))}
      </div>
      <div className="button-row">
        <Button disabled={item.comingSoon} onClick={() => onSave(item.type, config)}>Save</Button>
        {item.testable && <Button variant="secondary" onClick={() => onTest(item.type)}>Test</Button>}
      </div>
    </Panel>
  );
}
