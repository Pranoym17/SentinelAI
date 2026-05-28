import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api.js';
import CommanderStrip from '../components/CommanderStrip.jsx';
import FixPreviewPanel from '../components/FixPreviewPanel.jsx';
import IncidentCommandPanel from '../components/IncidentCommandPanel.jsx';
import { BriefsPanel, FollowupsPanel, GitHubEvidencePanel } from '../components/IncidentIntelligence.jsx';
import TimelineFeed from '../components/TimelineFeed.jsx';
import PostMortemViewer from '../components/PostMortemViewer.jsx';
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
          <h1>{incident ? `${incident.severity}: ${incident.service}` : 'Incident detail'}</h1>
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
          <CommanderStrip timeline={incident.timeline || []} />
          <div className="incident-detail-grid">
            <section className="stack">
              <Panel>
                <div className="incident-summary">
                  <div>
                    <span className="label">Hypothesis</span>
                    <h2>{incident.hypothesis || 'Root cause under investigation'}</h2>
                  </div>
                  <ConfidenceMeter value={incident.confidence || 0} />
                  <div className="summary-links">
                    <LinkLine label="Jira" value={incident.jira_ticket_id} href={incident.jira_ticket_url} />
                    <LinkLine label="GitHub PR" value={incident.github_pr?.title || incident.github_pr?.url} href={incident.github_pr?.url} />
                    <LinkLine label="Slack" value={incident.slack_message_ts ? `Message ${incident.slack_message_ts}` : ''} />
                  </div>
                </div>
              </Panel>
              <IncidentCommandPanel incident={incident} onRefresh={load} onResolved={setPostMortem} />
              <FixPreviewPanel incident={incident} onRefresh={load} />
              <PostMortemViewer incident={incident} markdown={postMortem} />
            </section>
            <aside className="stack">
              <BriefsPanel timeline={incident.timeline || []} />
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

function LinkLine({ label, value, href }) {
  return (
    <div className="link-line">
      <strong>{label}</strong>
      {href ? <a href={href} target="_blank" rel="noreferrer">{value || href}</a> : <span>{value || '—'}</span>}
    </div>
  );
}
