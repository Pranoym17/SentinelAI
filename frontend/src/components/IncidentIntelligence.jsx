import { engineerBrief, managerBrief, latestEvent, formatDateTime } from './incidentStory.js';
import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export function BriefsPanel({ incident, timeline = [] }) {
  return (
    <Panel>
      <SectionHeader title="Audience briefs" meta="Engineer and manager-ready status" />
      <div className="brief-grid">
        <Brief title="Engineer brief" copy={engineerBrief(incident, timeline)} />
        <Brief title="Manager brief" copy={managerBrief(incident, timeline)} />
      </div>
    </Panel>
  );
}

export function GitHubEvidencePanel({ incident }) {
  const timeline = incident?.timeline || [];
  const preview = incident?.fix_preview;
  const pr = incident?.github_pr;
  const evidence = collectEvidence(incident);

  return (
    <Panel>
      <SectionHeader
        title="GitHub evidence"
        meta={preview?.repo || pr?.repo || 'Commit correlation'}
        action={pr ? <StatusBadge status="PR opened" /> : preview ? <StatusBadge status="previewed" /> : null}
      />
      {evidence.length === 0 ? (
        <EmptyState title="No GitHub evidence yet" copy="Commit correlation and proposed files appear once GitHub data is available for this service." />
      ) : (
        <div className="evidence-list">
          {evidence.map((item, index) => (
            <div className="evidence-item" key={`${item.label}-${index}`}>
              <code>{item.label}</code>
              {item.href ? <a href={item.href} target="_blank" rel="noreferrer">{item.value}</a> : <span>{item.value}</span>}
            </div>
          ))}
          {latestEvent(timeline, 'github_fix_preview_generated') && (
            <div className="evidence-item">
              <code>artifact</code>
              <span>Fix preview generated from incident context and recent commits.</span>
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
      <SectionHeader title="Prevention follow-ups" meta="Jira tasks created after resolution" />
      {items.length === 0 ? (
        <EmptyState title="No prevention tasks yet" copy="Follow-up work is created after the post-mortem identifies prevention items." />
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
      <p>{copy || 'Brief will appear after response coordination.'}</p>
    </div>
  );
}

function collectEvidence(incident) {
  if (!incident) return [];
  const items = [];
  const preview = incident.fix_preview || {};
  const pr = incident.github_pr || {};
  if (preview.repo || pr.repo) items.push({ label: 'repo', value: preview.repo || pr.repo });
  if (pr.branch) items.push({ label: 'branch', value: pr.branch });
  if (pr.commit_sha) items.push({ label: 'commit', value: pr.commit_sha });
  if (pr.url) items.push({ label: 'pull request', value: pr.title || pr.url, href: pr.url });
  (preview.files || []).forEach((file) => {
    items.push({
      label: file.path || 'file',
      value: file.before_risk || file.proposed_change || 'Selected for remediation review.',
    });
  });
  (incident.reasoning_chain || []).forEach((line) => {
    const text = typeof line === 'string' ? line : `${line.step || ''} ${line.detail || ''}`;
    if (/commit|sha|github|changed file|deploy/i.test(text)) {
      items.push({ label: 'reasoning', value: text });
    }
  });
  const prEvent = latestEvent(incident.timeline || [], 'github_pr_created');
  if (prEvent?.occurred_at) items.push({ label: 'created', value: formatDateTime(prEvent.occurred_at) });
  return items;
}
