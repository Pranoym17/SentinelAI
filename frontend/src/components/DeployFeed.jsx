import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function DeployFeed({ deploys }) {
  return (
    <Panel className="compact">
      <SectionHeader title="Recent deploys" meta={`${deploys?.length || 0} entries`} />
      <div className="deploy-list">
        {(deploys || []).length === 0 && <EmptyState title="No deploys" copy="Recent deploys appear after demo seed." />}
        {(deploys || []).map((deploy) => (
          <article className="deploy-item" key={deploy.id}>
            <div>
              <strong>{deploy.service}</strong>
              <span>{deploy.version}</span>
            </div>
            <small>{new Date(deploy.deployed_at).toLocaleTimeString()} by {deploy.author}</small>
            {deploy.suspected_cause && <StatusBadge status="critical" />}
          </article>
        ))}
      </div>
    </Panel>
  );
}
