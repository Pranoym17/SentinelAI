import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card, StatusDot } from '../components/ui.jsx';

export default function ServicesPage() {
  const [services, setServices] = useState([]);
  const [sla, setSla] = useState([]);
  const [draft, setDraft] = useState({ name: '', display_name: '', team: '', sla_target: 99.9 });

  async function load() {
    const [serviceData, slaData] = await Promise.all([api.getServices(), api.getSla()]);
    setServices(serviceData.services || []);
    setSla(slaData.sla || []);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function create() {
    if (!draft.name) return;
    await api.createService(draft);
    setDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
    await load();
  }

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <p className="eyebrow">Catalog</p>
          <h1>Services</h1>
        </div>
      </div>
      <div className="service-grid">
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
        <button type="button" onClick={create}>Create service</button>
      </Card>
    </main>
  );
}
