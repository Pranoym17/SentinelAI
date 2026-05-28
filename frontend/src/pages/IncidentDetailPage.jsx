import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api.js';
import CommanderStrip from '../components/CommanderStrip.jsx';
import FixPreviewPanel from '../components/FixPreviewPanel.jsx';
import IncidentCommandPanel from '../components/IncidentCommandPanel.jsx';
import { BriefsPanel, FollowupsPanel, GitHubEvidencePanel } from '../components/IncidentIntelligence.jsx';
import TimelineFeed from '../components/TimelineFeed.jsx';
import PostMortemViewer from '../components/PostMortemViewer.jsx';
import { currentStage, durationText, formatDateTime, nextAction, reasoningText } from '../components/incidentStory.js';
import { ConfidenceMeter, Panel, SkeletonRows, StatusBadge } from '../components/ui.jsx';

export default function IncidentDetailPage() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [postMortem, setPostMortem] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.getIncident(id);
      setIncident(data);
      setPostMortem(data.post_mortem || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <h1>{incident ? `${incident.severity}: ${incident.service}` : 'Incident case file'}</h1>
        </div>
        {incident && (
          <div className="action-row">
            <StatusBadge status={incident.status} />
            <StatusBadge status={incident.severity} />
            {incident.github_pr && <StatusBadge status="PR opened" />}
          </div>
        )}
      </div>
      {error && <div className="notice">{error}</div>}
      {loading && <Panel><SkeletonRows rows={6} /></Panel>}
      {!loading && incident && (
        <>
          <CommanderStrip incident={incident} timeline={incident.timeline || []} />
          <div className="incident-detail-grid">
            <section className="stack">
              <IncidentSummary incident={incident} />
              <InvestigationPanel incident={incident} />
              <IncidentCommandPanel incident={incident} onRefresh={load} onResolved={setPostMortem} />
              <FixPreviewPanel incident={incident} onRefresh={load} />
              <PostMortemViewer incident={incident} markdown={postMortem} />
            </section>
            <aside className="stack">
              <BriefsPanel incident={incident} timeline={incident.timeline || []} />
              <ResponseArtifacts incident={incident} />
              <GitHubEvidencePanel incident={incident} />
              <FollowupsPanel timeline={incident.timeline || []} />
              <TimelineFeed timeline={incident.timeline || []} />
            </aside>
          </div>
        </>
      )}
    </main>
  );
}

function IncidentSummary({ incident }) {
  const stage = currentStage(incident, incident.timeline || []);
  return (
    <Panel>
      <div className="incident-summary">
        <div>
          <span className="label">Incident summary</span>
          <h2>{incident.hypothesis || 'Root cause under investigation'}</h2>
          <p className="muted">{nextAction(incident, incident.timeline || [])}</p>
        </div>
        <ConfidenceMeter value={incident.confidence || 0} />
        <div className="case-grid">
          <Fact label="Service" value={incident.service} />
          <Fact label="Severity" value={incident.severity} badge />
          <Fact label="Status" value={incident.status} badge />
          <Fact label="Current stage" value={stage?.label} />
          <Fact label="Signal" value={`${incident.signal_type || 'signal'} / ${incident.signal_value ?? 'pending'}`} />
          <Fact label="Detected" value={formatDateTime(incident.detected_at)} />
          <Fact label="Duration" value={durationText(incident)} />
          <Fact label="Affected teams" value={(incident.affected_teams || []).join(', ') || 'Not identified'} />
        </div>
      </div>
    </Panel>
  );
}

function InvestigationPanel({ incident }) {
  const reasoning = incident.reasoning_chain || [];
  const actions = incident.recommended_actions || [];
  return (
    <Panel>
      <SectionLike
        title="Agent investigation"
        meta="Evidence checked, hypothesis, and recommended engineering path."
        action={<StatusBadge status={`${incident.confidence || 0}% confidence`} />}
      />
      <div className="investigation-grid">
        <div className="info-box span-2">
          <strong>Reasoning chain</strong>
          {reasoning.length ? (
            <ol className="case-list">
              {reasoning.map((item, index) => (
                <li key={`${index}-${typeof item === 'string' ? item : item.step}`}>
                  {typeof item === 'string' ? item : `${item.step ? `${item.step}: ` : ''}${item.detail || ''}`}
                </li>
              ))}
            </ol>
          ) : (
            <span>No reasoning chain captured yet.</span>
          )}
        </div>
        <div className="info-box">
          <strong>Evidence summary</strong>
          <span>{reasoningText(incident) || 'Waiting for the investigator agent to attach evidence.'}</span>
        </div>
        <div className="info-box">
          <strong>Recommended actions</strong>
          {actions.length ? (
            <ul className="case-list">
              {actions.map((action) => <li key={action}>{action}</li>)}
            </ul>
          ) : (
            <span>No recommended actions captured yet.</span>
          )}
        </div>
      </div>
    </Panel>
  );
}

function ResponseArtifacts({ incident }) {
  return (
    <Panel>
      <SectionLike title="Response artifacts" meta="Operational evidence created by the response agents." />
      <div className="summary-links">
        <LinkLine label="Jira" value={incident.jira_ticket_id} href={incident.jira_ticket_url} />
        <LinkLine label="Slack" value={incident.slack_message_ts ? `Message ${incident.slack_message_ts}` : ''} />
        <LinkLine label="GitHub PR" value={incident.github_pr?.title || incident.github_pr?.url} href={incident.github_pr?.url} />
        <LinkLine label="Commit" value={incident.github_pr?.commit_sha || incident.fix_preview?.commit_sha} />
      </div>
    </Panel>
  );
}

function SectionLike({ title, meta, action }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {meta && <p>{meta}</p>}
      </div>
      {action}
    </div>
  );
}

function Fact({ label, value, badge = false }) {
  return (
    <div className="fact-card">
      <span>{label}</span>
      {badge ? <StatusBadge status={value || 'pending'} /> : <strong>{value || 'Pending'}</strong>}
    </div>
  );
}

function LinkLine({ label, value, href }) {
  return (
    <div className="link-line">
      <strong>{label}</strong>
      {href ? <a href={href} target="_blank" rel="noreferrer">{value || href}</a> : <span>{value || 'Not available yet'}</span>}
    </div>
  );
}
