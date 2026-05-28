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

import { Panel, SectionHeader } from './ui.jsx';

function formatHistory(history, service, metricType) {
  const points = history?.[service] || [];
  return points
    .filter((point) => point.metric_type === metricType)
    .slice(-60)
    .map((point) => ({
      time: new Date(point.recorded_at).toLocaleTimeString([], {
        minute: '2-digit',
        second: '2-digit',
      }),
      value: point.value,
    }));
}

export default function MetricChart({ history, deploys, incident }) {
  const service = incident?.service || 'payments';
  const metricType = incident?.signal_type === 'latency_spike' ? 'latency_ms' : 'error_rate';
  const data = formatHistory(history, service, metricType);
  const suspected = (deploys || []).find((deploy) => deploy.suspected_cause);
  const baseline = metricType === 'latency_ms' ? 150 : 0.2;
  const threshold = metricType === 'latency_ms' ? 2000 : 5;
  const label = metricType === 'latency_ms' ? 'latency' : 'error rate';

  return (
    <Panel>
      <SectionHeader
        title={`${service} ${label}`}
        meta={suspected ? `Suspected deploy: ${suspected.version}` : 'Last 60 readings'}
      />
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
            <ReferenceLine y={baseline} stroke="var(--healthy)" strokeDasharray="4 4" label="baseline" />
            <ReferenceLine y={threshold} stroke="var(--warning)" strokeDasharray="4 4" label="threshold" />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--critical)"
              strokeWidth={3}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
