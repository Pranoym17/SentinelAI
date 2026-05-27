export default function DeployFeed({ deploys }) {
  return (
    <section className="panel compact-panel">
      <p className="eyebrow">Recent Deploys</p>
      <div className="deploy-list">
        {(deploys || []).map((deploy) => (
          <article className={`deploy-item ${deploy.suspected_cause ? 'suspected' : ''}`} key={deploy.id}>
            <div>
              <strong>{deploy.service}</strong>
              <span>{deploy.version}</span>
            </div>
            <p>{deploy.changes_summary || 'No summary provided'}</p>
            <small>
              {new Date(deploy.deployed_at).toLocaleTimeString()} by {deploy.author}
            </small>
            {deploy.suspected_cause && <b>SUSPECTED CAUSE</b>}
          </article>
        ))}
      </div>
    </section>
  );
}
