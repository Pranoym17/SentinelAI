import { useState } from 'react';

import { api } from '../api.js';
import { Button, ConfidenceMeter, EmptyState, Panel, SectionHeader, StatusBadge, TerminalPanel } from './ui.jsx';

export default function IncidentCommandPanel({ incident, onRefresh, onResolved }) {
  const [query, setQuery] = useState("What's the status?");
  const [status, setStatus] = useState('');
  const [resolution, setResolution] = useState('Rolled back payments-api to v2.4.0');
  const [blastRadius, setBlastRadius] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!incident) {
    return (
      <Panel>
        <EmptyState title="◎ Monitoring active" copy="The agent is watching configured services. Incident controls appear here when an anomaly is detected." />
      </Panel>
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
    <Panel className="incident-panel">
      <SectionHeader
        title={`${incident.severity}: ${incident.service}`}
        meta={incident.hypothesis}
        action={
          <div className="action-row">
            <StatusBadge status={incident.severity} />
            {slaEvent && <StatusBadge status="SLA risk" />}
            {correlationEvent && <StatusBadge status="correlated" />}
          </div>
        }
      />

      <div className="info-grid">
        <Info title="Jira">
          {incident.jira_ticket_url ? <a href={incident.jira_ticket_url} target="_blank" rel="noreferrer">{incident.jira_ticket_id || 'View ticket'}</a> : '—'}
        </Info>
        <Info title="Slack">{slackEvent?.description || '—'}</Info>
        {oncallEvent && <Info title="On-call">{oncallEvent.description}</Info>}
        {runbookEvent && <Info title="Runbook">{runbookEvent.description}</Info>}
      </div>

      <div style={{ margin: '14px 0' }}>
        <ConfidenceMeter value={incident.confidence || 0} />
      </div>

      {(incident.recommended_actions || []).length > 0 && (
        <div className="info-box">
          <strong>Recommended actions</strong>
          <ul>
            {incident.recommended_actions.map((action) => <li key={action}>{action}</li>)}
          </ul>
        </div>
      )}

      <TerminalPanel title="reasoning" lines={incident.reasoning_chain || []} live={incident.status === 'open'} height={280} />

      <div className="form-grid" style={{ marginTop: 14 }}>
        <div className="field">
          <label>Status query</label>
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
        <div className="field">
          <label>Resolution</label>
          <input value={resolution} onChange={(event) => setResolution(event.target.value)} />
        </div>
      </div>
      <div className="button-row">
        <Button disabled={busy} onClick={askStatus}>Ask agent</Button>
        <Button disabled={busy} onClick={analyzeBlastRadius}>Analyze blast radius</Button>
        <Button variant="primary" disabled={busy || !resolution.trim()} onClick={resolve}>Resolve</Button>
      </div>
      {status && <p className="muted" style={{ marginTop: 10 }}>{status}</p>}

      {blastRadius && (
        <div className="modal-backdrop" role="dialog" aria-label="Blast radius analysis">
          <div className="modal-panel">
            <SectionHeader
              title={`${blastRadius.risk_level} rollback risk`}
              meta={blastRadius.warning || 'No connected services found.'}
              action={<Button variant="ghost" size="sm" onClick={() => setBlastRadius(null)}>Close</Button>}
            />
            <BlastGrid blastRadius={blastRadius} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function Info({ title, children }) {
  return (
    <div className="info-box">
      <strong>{title}</strong>
      <span>{children}</span>
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
