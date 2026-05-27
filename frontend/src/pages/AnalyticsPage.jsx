import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api.js';
import { Card, EmptyState } from '../components/ui.jsx';

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
          <p className="eyebrow">Reliability</p>
          <h1>Analytics</h1>
        </div>
      </div>
      {error && <div className="notice">{error}</div>}
      {loading && <Card><EmptyState title="Loading analytics" copy="Calculating reliability metrics." /></Card>}
      <div className="stats-grid">
        <Card><p className="eyebrow">MTTD</p><h2>{analytics?.mttd_seconds ?? 0}s</h2></Card>
        <Card><p className="eyebrow">MTTR</p><h2>{analytics?.mttr_minutes ?? 0}m</h2></Card>
        <Card><p className="eyebrow">Total incidents</p><h2>{analytics?.total_incidents ?? 0}</h2></Card>
        <Card><p className="eyebrow">SLA compliance</p><h2>{analytics?.sla_compliance ?? 100}%</h2></Card>
      </div>
      <Card>
        <p className="eyebrow">Incidents by service</p>
        {chartData.length === 0 ? <EmptyState title="No resolved incidents" copy="Resolve an incident to populate this chart." /> : <div className="chart-wrap small">
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
      </Card>
      <Card>
        <p className="eyebrow">SLA status</p>
        {sla.length === 0 ? <EmptyState title="No SLA records" copy="Add services or resolve incidents to generate SLA records." /> : <div className="data-table">
          {sla.map((row) => (
            <div className="table-row" key={row.service}>
              <span>{row.service}</span>
              <span>{row.target_uptime}% target</span>
              <span>{row.actual_uptime}% actual</span>
              <span>{row.remaining_budget_minutes}m left</span>
            </div>
          ))}
        </div>}
      </Card>
    </main>
  );
}
