import { useState } from 'react';
import { AlertTriangle, CheckCircle2, ExternalLink, MessageSquare, Network, ShieldAlert } from 'lucide-react';

import { api } from '../api.js';
import { TerminalPanel } from './ui.jsx';

export default function IncidentCommandPanel({ incident, onRefresh, onResolved }) {
  const [query, setQuery] = useState("What's the status?");
  const [status, setStatus] = useState('');
  const [resolution, setResolution] = useState('Rolled back payments-api to v2.4.0');
  const [blastRadius, setBlastRadius] = useState(null);
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

  const timeline = incident.timeline || [];
  const oncallEvent = timeline.find((event) => event.event_type === 'oncall_identified');
  const slaEvent = timeline.find((event) => event.event_type === 'sla_warning');
  const correlationEvent = timeline.find((event) => event.event_type === 'correlation_detected');
  const runbookEvent = timeline.find((event) => event.event_type === 'runbook_success_recorded');
  const slackEvent = timeline.find((event) => event.event_type.startsWith('slack_'));

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

  async function analyzeBlastRadius() {
    setBusy(true);
    try {
      const data = await api.analyzeBlastRadius(incident.incident_id);
      setBlastRadius(data);
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
          <h2 className="incident-title">
            <span>{incident.severity}: {incident.service}</span>
            {slaEvent && <span className="header-badge warning">SLA risk</span>}
            {correlationEvent && <span className="header-badge">Correlated</span>}
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
        {slackEvent ? (
          <span>
            <CheckCircle2 size={16} />
            {slackEvent.event_type.replaceAll('_', ' ')}
          </span>
        ) : (
          <span>Slack pending</span>
        )}
        {oncallEvent && <span>On-call found</span>}
      </div>

      <div className="status-grid">
        <div>
          <strong>Jira</strong>
          {incident.jira_ticket_url ? (
            <a href={incident.jira_ticket_url} target="_blank" rel="noreferrer">{incident.jira_ticket_id}</a>
          ) : (
            <span>Not created</span>
          )}
        </div>
        <div>
          <strong>Slack</strong>
          <span>{slackEvent?.description || 'No Slack event yet'}</span>
        </div>
      </div>

      {(incident.recommended_actions || []).length > 0 && (
        <div className="insight-box">
          <strong>Recommended actions</strong>
          <ul>
            {incident.recommended_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      {(oncallEvent || slaEvent || correlationEvent) && (
        <div className="insight-grid">
          {oncallEvent && <Insight title="On-call" copy={oncallEvent.description} />}
          {slaEvent && <Insight title="SLA" copy={slaEvent.description} />}
          {correlationEvent && <Insight title="Correlation" copy={correlationEvent.description} />}
        </div>
      )}

      {(runbookEvent || incident.matched_past_incident_id) && (
        <div className="warning-box neutral">
          <AlertTriangle size={18} />
          <span>{runbookEvent?.description || `Matched historical incident #${incident.matched_past_incident_id}`}</span>
        </div>
      )}

      <TerminalPanel title="Reasoning chain" lines={incident.reasoning_chain || []} />

      <div className="query-row">
        <MessageSquare size={18} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
        <button type="button" disabled={busy} onClick={askStatus}>Ask</button>
      </div>
      {status && <p className="status-response">{status}</p>}

      <div className="query-row">
        <Network size={18} />
        <button type="button" disabled={busy} onClick={analyzeBlastRadius}>Analyze blast radius</button>
      </div>
      {blastRadius && (
        <div className="modal-backdrop" role="dialog" aria-label="Blast radius analysis">
          <div className="modal-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Blast radius</p>
                <h2>{blastRadius.risk_level} risk</h2>
              </div>
              <button type="button" className="ghost-button icon-button" onClick={() => setBlastRadius(null)}>x</button>
            </div>
            <p className="muted">{blastRadius.warning || 'No connected services found.'}</p>
            <BlastGrid blastRadius={blastRadius} />
          </div>
        </div>
      )}

      <div className="query-row">
        <CheckCircle2 size={18} />
        <input value={resolution} onChange={(event) => setResolution(event.target.value)} />
        <button type="button" disabled={busy || !resolution.trim()} onClick={resolve}>Resolve</button>
      </div>
    </section>
  );
}

function Insight({ title, copy }) {
  return (
    <div>
      <strong>{title}</strong>
      <span>{copy}</span>
    </div>
  );
}

export function BlastGrid({ blastRadius }) {
  return (
    <div className="blast-grid">
      <div>
        <strong>Upstream</strong>
        {(blastRadius.upstream_dependencies || []).length ? (
          blastRadius.upstream_dependencies.map((service) => <span key={service}>{service}</span>)
        ) : (
          <small>None recorded</small>
        )}
      </div>
      <div>
        <strong>Downstream</strong>
        {(blastRadius.downstream_dependents || []).length ? (
          blastRadius.downstream_dependents.map((service) => <span key={service}>{service}</span>)
        ) : (
          <small>None recorded</small>
        )}
      </div>
    </div>
  );
}
