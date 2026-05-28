import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function MetricsPanel({ metrics }) {
  return (
    <Panel>
      <SectionHeader title="Watched services" meta={`${metrics.length} configured`} />
      {metrics.length === 0 ? (
        <EmptyState title="No metrics" copy="Metrics appear after demo seed or worker updates." />
      ) : (
        <div className="service-grid">
          {metrics.map((service) => {
            const status = service.error_rate?.status || 'healthy';
            return (
              <article className={`panel compact service-card ${status}`} key={service.service}>
                <div className="service-card-head">
                  <div>
                    <h3>{service.service}</h3>
                    <small className="muted">live worker feed</small>
                  </div>
                  <StatusBadge status={status} />
                </div>
                <dl>
                  <div>
                    <dt>Error rate</dt>
                    <dd>{service.error_rate?.value ?? 0}%</dd>
                  </div>
                  <div>
                    <dt>Latency</dt>
                    <dd>{service.latency_ms?.value ?? 0}ms</dd>
                  </div>
                </dl>
              </article>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
