import { Activity, Gauge } from 'lucide-react';

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function MetricsPanel({ metrics }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Live Metrics</p>
          <h2>Watched services</h2>
        </div>
        <Activity size={22} />
      </div>

      <div className="metric-grid">
        {metrics.map((service) => (
          <article className="metric-card" key={service.service}>
            <div className="metric-card-head">
              <strong>{service.service}</strong>
              <StatusBadge status={service.error_rate?.status || 'normal'} />
            </div>
            <div className="metric-row">
              <Gauge size={18} />
              <span>Error rate</span>
              <strong>{service.error_rate?.value ?? 0}%</strong>
            </div>
            <div className="metric-row">
              <Gauge size={18} />
              <span>Latency</span>
              <strong>{service.latency_ms?.value ?? 0}ms</strong>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
