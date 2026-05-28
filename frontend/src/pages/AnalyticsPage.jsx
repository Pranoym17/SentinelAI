import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api.js';
import { DataTable, EmptyState, MetricCell, Panel, SkeletonRows, TableHeader, TableRow, SectionHeader } from '../components/ui.jsx';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [sla, setSla] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.getAnalytics(), api.getSla()])
      .then(([analyticsData, slaData]) => {
        setAnalytics(analyticsData);
        setSla(slaData.sla || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const chartData = Object.entries(analytics?.by_service || {}).map(([service, count]) => ({ service, count }));

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <h1>Analytics</h1>
        </div>
      </div>
      {error && <div className="notice">{error}</div>}
      {loading && <Panel><SkeletonRows rows={4} /></Panel>}
      <div className="stats-row">
        <MetricCell label="MTTD" value={analytics?.mttd_seconds ?? 0} unit="s" />
        <MetricCell label="MTTR" value={analytics?.mttr_minutes ?? 0} unit="m" />
        <MetricCell label="Incidents" value={analytics?.total_incidents ?? 0} />
        <MetricCell label="SLA compliance" value={analytics?.sla_compliance ?? 100} unit="%" status={(analytics?.sla_compliance ?? 100) < 100 ? 'warning' : 'healthy'} />
        <MetricCell label="Agent accuracy" value={analytics?.agent_accuracy ?? 0} unit="%" />
      </div>
      <Panel>
        <SectionHeader title="Incidents by service" />
        {chartData.length === 0 ? <EmptyState title="◎ Not enough data yet" copy="Analytics populate after your first resolved incident. The agent is monitoring. Check back soon." /> : <div className="chart-wrap small">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="service" stroke="var(--text-secondary)" />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }} />
              <Bar dataKey="count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>}
      </Panel>
      <Panel>
        <SectionHeader title="SLA status" />
        {sla.length === 0 ? <EmptyState title="◎ Not enough SLA data yet" copy="SLA records appear after services are configured and incidents resolve." /> : <DataTable columns="1fr 120px 120px 120px">
          <TableHeader cells={['Service', 'Target', 'Actual', 'Budget']} />
          {sla.map((row) => (
            <TableRow key={row.service}>
              <span>{row.service || '—'}</span>
              <span>{row.target_uptime}%</span>
              <span>{row.actual_uptime}%</span>
              <span>{row.remaining_budget_minutes}m</span>
            </TableRow>
          ))}
        </DataTable>}
      </Panel>
    </main>
  );
}
