import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card, EmptyState, StatusDot } from '../components/ui.jsx';

export default function ServicesPage() {
  const [services, setServices] = useState([]);
  const [sla, setSla] = useState([]);
  const [draft, setDraft] = useState({ name: '', display_name: '', team: '', sla_target: 99.9 });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [serviceData, slaData] = await Promise.all([api.getServices(), api.getSla()]);
      setServices(serviceData.services || []);
      setSla(slaData.sla || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function create() {
    if (!draft.name) return;
    setBusy(true);
    setError('');
    try {
      await api.createService(draft);
      setDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
      setMessage('Service created');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <p className="eyebrow">Catalog</p>
          <h1>Services</h1>
        </div>
      </div>
      {message && <div className="notice success">{message}</div>}
      {error && <div className="notice">{error}</div>}
      {loading && <Card><EmptyState title="Loading services" copy="Fetching service catalog and SLA records." /></Card>}
      <div className="service-grid">
        {!loading && services.length === 0 && (
          <Card><EmptyState title="No services configured" copy="Add the first monitored service below." /></Card>
        )}
        {services.map((service) => {
          const status = sla.find((item) => item.service === service.name);
          return (
            <Card key={service.id}>
              <div className="section-heading">
                <h2>{service.display_name || service.name}</h2>
                <StatusDot status={status?.status === 'healthy' ? 'normal' : 'warning'} />
              </div>
              <p className="muted">{service.description || 'No description yet.'}</p>
              <div className="mini-stats">
                <span>{service.team || 'No team'}</span>
                <span>{service.sla_target}% SLA</span>
                <span>{status?.remaining_budget_minutes ?? 'n/a'}m budget</span>
              </div>
            </Card>
          );
        })}
      </div>
      <Card>
        <p className="eyebrow">Add service</p>
        <div className="form-grid">
          <input placeholder="name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
          <input placeholder="display name" value={draft.display_name} onChange={(event) => setDraft({ ...draft, display_name: event.target.value })} />
          <input placeholder="team" value={draft.team} onChange={(event) => setDraft({ ...draft, team: event.target.value })} />
          <input type="number" value={draft.sla_target} onChange={(event) => setDraft({ ...draft, sla_target: Number(event.target.value) })} />
        </div>
        <button type="button" disabled={busy || !draft.name.trim()} onClick={create}>
          {busy ? 'Creating...' : 'Create service'}
        </button>
      </Card>
    </main>
  );
}
