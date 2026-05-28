import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { Button, EmptyState, Panel, SectionHeader, SkeletonRows, StatusBadge } from '../components/ui.jsx';

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
  const [busy, setBusy] = useState('');

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
    setBusy(`save-${type}`);
    try {
      await api.saveIntegration({ type, enabled: true, config });
      setMessage(`${type} saved`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function testIntegration(type) {
    setError('');
    setBusy(`test-${type}`);
    try {
      const result = await api.testIntegration(type);
      setMessage(`${type} test: ${result.ok || result.posted || result.created ? 'passed' : result.reason || 'completed'}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function saveOncall() {
    setError('');
    setBusy('oncall');
    try {
      await api.createOncall(oncall);
      setMessage('On-call schedule saved');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function createService() {
    if (!serviceDraft.name) return;
    setError('');
    setBusy('service');
    try {
      await api.createService(serviceDraft);
      setServiceDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
      setMessage('Service created');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
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

      {loading && <Panel><SkeletonRows rows={6} /></Panel>}

      {tab === 'integrations' && !loading && (
        <div className="card-grid three">
          {integrationTypes.map((item) => (
            <IntegrationCard
              key={item.type}
              item={item}
              saved={integrationMap[item.type]}
              onSave={saveIntegration}
              onTest={testIntegration}
              busy={busy}
            />
          ))}
        </div>
      )}

      {tab === 'services' && !loading && (
        <>
          <div className="card-grid three">
            {services.length === 0 && <Panel><EmptyState title="No services configured" copy="Add services here so the agent knows what to monitor." /></Panel>}
            {services.map((service) => (
              <Panel key={service.id}>
                <span className="label">{service.team || '—'}</span>
                <h2>{service.display_name || service.name}</h2>
                <p className="muted">{service.sla_target}% SLA target</p>
              </Panel>
            ))}
          </div>
          <Panel>
            <SectionHeader title="Add service" />
            <div className="form-grid">
              <label className="field"><span>Name</span><input placeholder="name" value={serviceDraft.name} onChange={(event) => setServiceDraft({ ...serviceDraft, name: event.target.value })} /></label>
              <label className="field"><span>Display name</span><input placeholder="display name" value={serviceDraft.display_name} onChange={(event) => setServiceDraft({ ...serviceDraft, display_name: event.target.value })} /></label>
              <label className="field"><span>Team</span><input placeholder="team" value={serviceDraft.team} onChange={(event) => setServiceDraft({ ...serviceDraft, team: event.target.value })} /></label>
              <label className="field"><span>SLA target</span><input type="number" value={serviceDraft.sla_target} onChange={(event) => setServiceDraft({ ...serviceDraft, sla_target: Number(event.target.value) })} /></label>
            </div>
            <Button loading={busy === 'service'} disabled={!serviceDraft.name.trim()} onClick={createService}>Create service</Button>
          </Panel>
        </>
      )}

      {tab === 'on-call' && !loading && (
        <Panel>
          <SectionHeader title="On-call schedule" />
          <div className="form-grid">
            <label className="field"><span>Engineer name</span><input placeholder="Engineer name" value={oncall.engineer_name} onChange={(event) => setOncall({ ...oncall, engineer_name: event.target.value })} /></label>
            <label className="field"><span>Slack handle</span><input placeholder="@slack" value={oncall.slack_handle} onChange={(event) => setOncall({ ...oncall, slack_handle: event.target.value })} /></label>
            <label className="field"><span>Team</span><input placeholder="team" value={oncall.team} onChange={(event) => setOncall({ ...oncall, team: event.target.value })} /></label>
            <label className="field"><span>Start time</span><input type="datetime-local" value={oncall.start_time} onChange={(event) => setOncall({ ...oncall, start_time: event.target.value })} /></label>
            <label className="field"><span>End time</span><input type="datetime-local" value={oncall.end_time} onChange={(event) => setOncall({ ...oncall, end_time: event.target.value })} /></label>
          </div>
          {!oncall.engineer_name && (
            <EmptyState title="No on-call schedule configured" copy="Add engineers in Settings → On-call." />
          )}
          <Button loading={busy === 'oncall'} disabled={!oncall.engineer_name} onClick={saveOncall}>Save on-call</Button>
        </Panel>
      )}
    </main>
  );
}

function IntegrationCard({ item, saved, onSave, onTest, busy }) {
  const [config, setConfig] = useState(saved?.config || {});
  const hasSavedValues = !item.comingSoon && item.fields.some((field) => Boolean(saved?.config?.[field]));
  useEffect(() => {
    setConfig(saved?.config || {});
  }, [saved?.id]);

  return (
    <Panel>
      <div className="service-card-head">
        <StatusBadge status={item.comingSoon ? 'neutral' : saved?.enabled ? 'healthy' : 'critical'} />
        {!item.comingSoon && (
          <span className={`connection-badge ${hasSavedValues ? 'connected' : 'missing'}`}>
            {hasSavedValues ? 'Connected' : 'Not configured'}
          </span>
        )}
      </div>
      <h2>{item.title}</h2>
      {item.comingSoon && <p className="muted">Available soon</p>}
      <div className="form-grid single">
        {!item.comingSoon && item.fields.map((field) => (
          <label className="field" key={field}>
            <span>{field.replaceAll('_', ' ')}</span>
            <input
              placeholder={field}
              type={field.includes('token') || field.includes('key') ? 'password' : 'text'}
              value={config[field] || ''}
              onChange={(event) => setConfig({ ...config, [field]: event.target.value })}
            />
          </label>
        ))}
      </div>
      <div className="button-row">
        {item.comingSoon ? (
          <span className="label">Available soon</span>
        ) : (
          <>
            <Button loading={busy === `save-${item.type}`} onClick={() => onSave(item.type, config)}>Save</Button>
            {item.testable && <Button loading={busy === `test-${item.type}`} variant="secondary" onClick={() => onTest(item.type)}>Test</Button>}
          </>
        )}
      </div>
    </Panel>
  );
}
