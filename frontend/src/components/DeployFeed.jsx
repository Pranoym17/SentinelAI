import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function DeployFeed({ deploys }) {
  return (
    <Panel className="compact">
      <SectionHeader title="Recent deploys" meta={`${deploys?.length || 0} entries`} />
      <div className="deploy-list">
        {(deploys || []).length === 0 && <EmptyState title="No recent deploys" copy="Deploy records appear here when the agent receives deployment history." />}
        {(deploys || []).map((deploy) => (
          <article className="deploy-item" key={deploy.id}>
            <div>
              <strong>{deploy.service}</strong>
              <span>{deploy.version}</span>
            </div>
            <small>{new Date(deploy.deployed_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} by {deploy.author || '—'}</small>
            {deploy.suspected_cause && <StatusBadge status="critical" />}
          </article>
        ))}
      </div>
    </Panel>
  );
}
