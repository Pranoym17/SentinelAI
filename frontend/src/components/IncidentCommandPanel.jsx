import { useState } from 'react';

import { api } from '../api.js';
import { artifactBadges, nextAction } from './incidentStory.js';
import { Button, ConfidenceMeter, EmptyState, Panel, SectionHeader, StatusBadge, TerminalPanel } from './ui.jsx';

export default function IncidentCommandPanel({ incident, onRefresh, onResolved }) {
  const [query, setQuery] = useState("What's the status?");
  const [status, setStatus] = useState('');
  const [resolution, setResolution] = useState('Rolled back payments-api to v2.4.0');
  const [blastRadius, setBlastRadius] = useState(null);
  const [busy, setBusy] = useState('');
  const [feedback, setFeedback] = useState('');

  if (!incident) {
    return (
      <Panel>
        <EmptyState title="Monitoring active" copy="The agent is watching configured services. Incident controls appear here when an anomaly is detected." />
      </Panel>
    );
  }

  const timeline = incident.timeline || [];
  const oncallEvent = timeline.find((event) => event.event_type === 'oncall_identified');
  const slaEvent = timeline.find((event) => event.event_type === 'sla_warning');
  const correlationEvent = timeline.find((event) => event.event_type === 'correlation_detected');
  const runbookEvent = timeline.find((event) => event.event_type === 'runbook_success_recorded');
  const slackEvent = timeline.find((event) => event.event_type.startsWith('slack_'));
  const artifacts = artifactBadges(incident, timeline);

  async function askStatus() {
    setBusy('status');
    setFeedback('');
    try {
      const data = await api.queryStatus(query, incident.incident_id);
      setStatus(data.response);
      setFeedback('Agent status response received.');
    } catch (err) {
      setFeedback(err.message);
    } finally {
      setBusy('');
    }
  }

  async function resolve() {
    setBusy('resolve');
    setFeedback('');
    try {
      const data = await api.resolveIncident(incident.incident_id, resolution);
      onResolved(data.post_mortem);
      await onRefresh();
      setFeedback('Incident resolved and post-mortem generated.');
    } catch (err) {
      setFeedback(err.message);
    } finally {
      setBusy('');
    }
  }

  async function analyzeBlastRadius() {
    setBusy('blast');
    setFeedback('');
    try {
      const data = await api.analyzeBlastRadius(incident.incident_id);
      setBlastRadius(data);
      await onRefresh();
      setFeedback('Blast radius analysis ready.');
    } catch (err) {
      setFeedback(err.message);
    } finally {
      setBusy('');
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

      <div className="next-action-card">
        <span className="label">Recommended next step</span>
        <strong>{nextAction(incident, timeline)}</strong>
        {artifacts.length > 0 && (
          <div className="artifact-row">
            {artifacts.map(([label, statusValue]) => (
              <span className={`artifact-pill ${statusValue}`} key={label}>{label}</span>
            ))}
          </div>
        )}
      </div>

      <div className="info-grid">
        <Info title="Jira">
          {incident.jira_ticket_url ? <a href={incident.jira_ticket_url} target="_blank" rel="noreferrer">{incident.jira_ticket_id || 'View ticket'}</a> : 'Not created yet'}
        </Info>
        <Info title="Slack">{slackEvent?.description || 'Not posted yet'}</Info>
        {oncallEvent && <Info title="On-call">{oncallEvent.description}</Info>}
        {runbookEvent && <Info title="Runbook">{runbookEvent.description}</Info>}
      </div>

      <div style={{ margin: '14px 0' }}>
        <ConfidenceMeter value={incident.confidence || 0} />
      </div>

      {(incident.recommended_actions || []).length > 0 && (
        <div className="info-box">
          <strong>Recommended engineering actions</strong>
          <ul className="case-list">
            {incident.recommended_actions.map((action) => <li key={action}>{action}</li>)}
          </ul>
        </div>
      )}

      <TerminalPanel title="reasoning" lines={incident.reasoning_chain || []} live={incident.status === 'open'} height={280} />

      <div className="form-grid" style={{ marginTop: 14 }}>
        <label className="field">
          <span>Status query</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label className="field">
          <span>Resolution summary</span>
          <input value={resolution} onChange={(event) => setResolution(event.target.value)} />
        </label>
      </div>
      <div className="button-row">
        <Button loading={busy === 'status'} disabled={Boolean(busy)} onClick={askStatus}>Ask agent</Button>
        <Button loading={busy === 'blast'} disabled={Boolean(busy)} onClick={analyzeBlastRadius}>Analyze blast radius</Button>
        <Button variant="primary" loading={busy === 'resolve'} disabled={Boolean(busy) || !resolution.trim()} onClick={resolve}>Resolve incident</Button>
      </div>
      {status && <p className="muted" style={{ marginTop: 10 }}>{status}</p>}
      {feedback && <div className={feedback.includes('ready') || feedback.includes('received') || feedback.includes('resolved') ? 'notice success' : 'notice'}>{feedback}</div>}

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
