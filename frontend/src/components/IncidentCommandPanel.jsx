import { useState } from 'react';
import { CheckCircle2, ExternalLink, MessageSquare, ShieldAlert } from 'lucide-react';

import { api } from '../api.js';

export default function IncidentCommandPanel({ incident, onRefresh, onResolved }) {
  const [query, setQuery] = useState("What's the status?");
  const [status, setStatus] = useState('');
  const [resolution, setResolution] = useState('Rolled back payments-api to v2.4.0');
  const [busy, setBusy] = useState(false);

  if (!incident) {
    return (
      <section className="panel empty-incident">
        <ShieldAlert size={28} />
        <h2>No active incident</h2>
        <p className="muted">Monitoring is active. Start the autonomous demo or inject a signal.</p>
      </section>
    );
  }

  async function askStatus() {
    setBusy(true);
    try {
      const data = await api.queryStatus(query, incident.incident_id);
      setStatus(data.response);
    } finally {
      setBusy(false);
    }
  }

  async function resolve() {
    setBusy(true);
    try {
      const data = await api.resolveIncident(incident.incident_id, resolution);
      onResolved(data.post_mortem);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel incident-panel command-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Incident Command</p>
          <h2>
            {incident.severity}: {incident.service}
          </h2>
        </div>
        <div className="confidence">{incident.confidence}%</div>
      </div>

      <p className="hypothesis">{incident.hypothesis}</p>

      <div className="action-strip">
        {incident.jira_ticket_url ? (
          <a href={incident.jira_ticket_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} />
            {incident.jira_ticket_id}
          </a>
        ) : (
          <span>Jira pending</span>
        )}
        {(incident.timeline || []).some((event) => event.event_type === 'slack_sent') ? (
          <span>
            <CheckCircle2 size={16} />
            Slack sent
          </span>
        ) : (
          <span>Slack pending</span>
        )}
      </div>

      <div className="reasoning-box">
        {(incident.reasoning_chain || []).map((step, index) => (
          <div className="reasoning-step" key={`${step.step}-${index}`}>
            <div>
              <strong>{step.step}</strong>
              <span>{step.confidence}%</span>
            </div>
            <p>{step.detail}</p>
          </div>
        ))}
      </div>

      <div className="query-row">
        <MessageSquare size={18} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
        <button type="button" disabled={busy} onClick={askStatus}>
          Ask
        </button>
      </div>
      {status && <p className="status-response">{status}</p>}

      <div className="query-row">
        <CheckCircle2 size={18} />
        <input value={resolution} onChange={(event) => setResolution(event.target.value)} />
        <button type="button" disabled={busy || !resolution.trim()} onClick={resolve}>
          Resolve
        </button>
      </div>
    </section>
  );
}
