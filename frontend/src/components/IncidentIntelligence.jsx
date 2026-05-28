import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export function BriefsPanel({ timeline = [] }) {
  const event = latestEvent(timeline, 'communication_briefs_generated');
  const engineer = event?.metadata?.engineer_brief;
  const manager = event?.metadata?.manager_brief;

  return (
    <Panel>
      <SectionHeader title="Slack briefs" meta="Engineer and manager variants" />
      {!engineer && !manager ? (
        <EmptyState title="◎ No briefs generated" copy="Briefs are generated when the response agent coordinates Slack updates." />
      ) : (
        <div className="brief-grid">
          <Brief title="Engineer brief" copy={engineer} />
          <Brief title="Manager brief" copy={manager} />
        </div>
      )}
    </Panel>
  );
}

export function GitHubEvidencePanel({ incident }) {
  const preview = incident?.fix_preview;
  const pr = incident?.github_pr;
  const commitLines = (incident?.reasoning_chain || []).filter((line) => {
    const text = typeof line === 'string' ? line : `${line.step || ''} ${line.detail || ''}`;
    return /commit|sha|github|changed file/i.test(text);
  });

  return (
    <Panel>
      <SectionHeader
        title="GitHub evidence"
        meta={preview?.repo || 'Commit correlation'}
        action={pr ? <StatusBadge status="PR opened" /> : preview ? <StatusBadge status="previewed" /> : null}
      />
      {!preview && commitLines.length === 0 ? (
        <EmptyState title="◎ No GitHub evidence yet" copy="Recent commits and fix evidence appear after GitHub is configured for the service." />
      ) : (
        <div className="evidence-list">
          {commitLines.map((line, index) => (
            <EvidenceLine line={line} key={index} />
          ))}
          {(preview?.files || []).map((file) => (
            <div className="evidence-item" key={file.path || file.proposed_change}>
              <code>{file.path || 'unknown file'}</code>
              <span>{file.before_risk || file.proposed_change || 'File selected for review.'}</span>
            </div>
          ))}
          {pr?.url && (
            <div className="evidence-item">
              <code>pull request</code>
              <a href={pr.url} target="_blank" rel="noreferrer">{pr.title || pr.url}</a>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

export function FollowupsPanel({ timeline = [] }) {
  const event = latestEvent(timeline, 'jira_followups_created');
  const items = event?.metadata?.items || event?.metadata?.followups || event?.metadata?.subtasks || [];

  return (
    <Panel>
      <SectionHeader title="Jira follow-ups" meta="Post-mortem action items" />
      {items.length === 0 ? (
        <EmptyState title="≡ No follow-ups yet" copy="Jira follow-up tasks are created after a resolved incident has a post-mortem." />
      ) : (
        <div className="followup-list">
          {items.map((item, index) => (
            <div className="followup-item" key={item.key || item.title || index}>
              <StatusBadge status={item.priority || item.status || 'task'} />
              <div>
                <strong>{item.title || item.summary || item.key || 'Follow-up task'}</strong>
                {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.key || item.url}</a> : <span>{item.key || 'Tracked in Jira'}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Brief({ title, copy }) {
  return (
    <div className="brief-card">
      <strong>{title}</strong>
      <p>{copy || 'No brief available.'}</p>
    </div>
  );
}

function EvidenceLine({ line }) {
  const text = typeof line === 'string' ? line : `${line.step ? `[${line.step}] ` : ''}${line.detail || ''}`;
  return (
    <div className="evidence-item">
      <code>reasoning</code>
      <span>{text}</span>
    </div>
  );
}

function latestEvent(timeline, type) {
  return [...(timeline || [])].reverse().find((event) => event.event_type === type);
}
