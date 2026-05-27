import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function formatHistory(history) {
  const payments = history?.payments || [];
  return payments
    .filter((point) => point.metric_type === 'error_rate')
    .slice(-60)
    .map((point) => ({
      time: new Date(point.recorded_at).toLocaleTimeString([], {
        minute: '2-digit',
        second: '2-digit',
      }),
      error_rate: point.value,
    }));
}

export default function MetricChart({ history, deploys }) {
  const data = formatHistory(history);
  const suspected = (deploys || []).find((deploy) => deploy.suspected_cause);

  return (
    <section className="panel chart-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Payments Error Rate</p>
          <h2>Live signal</h2>
        </div>
        {suspected && <span className="suspected-label">SUSPECTED CAUSE: {suspected.version}</span>}
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="var(--text-secondary)" minTickGap={28} />
            <YAxis stroke="var(--text-secondary)" domain={[0, 'dataMax + 2']} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }}
              labelStyle={{ color: 'var(--text-primary)' }}
            />
            <ReferenceLine y={0.2} stroke="var(--healthy)" strokeDasharray="4 4" label="baseline" />
            <ReferenceLine y={5} stroke="var(--warning)" strokeDasharray="4 4" label="threshold" />
            <Line
              type="monotone"
              dataKey="error_rate"
              stroke="var(--critical)"
              strokeWidth={3}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
