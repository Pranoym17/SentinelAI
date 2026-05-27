import { useState } from 'react';
import { CheckCircle2, ExternalLink, MessageSquare } from 'lucide-react';

import { api } from '../api.js';

export default function IncidentPanel({ incident, onResolved }) {
  const [query, setQuery] = useState("What's the status?");
  const [statusResponse, setStatusResponse] = useState('');
  const [resolutionText, setResolutionText] = useState('Rolled back payments-api to v2.4.0');
  const [busy, setBusy] = useState(false);

  async function askStatus() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const data = await api.queryStatus(query, incident.incident_id);
      setStatusResponse(data.response);
    } finally {
      setBusy(false);
    }
  }

  async function resolveIncident() {
    if (!resolutionText.trim()) return;
    setBusy(true);
    try {
      const data = await api.resolveIncident(incident.incident_id, resolutionText);
      onResolved(data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel incident-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Active Incident</p>
          <h2>
            {incident.severity}: {incident.service}
          </h2>
        </div>
        <div className="confidence">{incident.confidence}%</div>
      </div>

      <p className="hypothesis">{incident.hypothesis}</p>

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

      <div className="two-column">
        <div>
          <h3>Actions</h3>
          <ul className="clean-list">
            {(incident.actions_taken || []).length === 0 && <li>No external actions completed yet.</li>}
            {(incident.actions_taken || []).map((action) => (
              <li key={action}>
                <CheckCircle2 size={16} />
                {action}
              </li>
            ))}
            {incident.jira_ticket_url && (
              <li>
                <ExternalLink size={16} />
                <a href={incident.jira_ticket_url} target="_blank" rel="noreferrer">
                  {incident.jira_ticket_id || 'View Jira ticket'}
                </a>
              </li>
            )}
          </ul>
        </div>
        <div>
          <h3>Timeline</h3>
          <ul className="timeline">
            {(incident.timeline || []).map((event) => (
              <li key={event.id || `${event.event_type}-${event.occurred_at}`}>
                <span>{event.event_type}</span>
                {event.description}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="query-row">
        <MessageSquare size={18} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
        <button type="button" disabled={busy} onClick={askStatus}>
          Ask
        </button>
      </div>
      {statusResponse && <p className="status-response">{statusResponse}</p>}

      <div className="query-row">
        <CheckCircle2 size={18} />
        <input value={resolutionText} onChange={(event) => setResolutionText(event.target.value)} />
        <button type="button" disabled={busy || !resolutionText.trim()} onClick={resolveIncident}>
          Resolve
        </button>
      </div>
    </section>
  );
}
