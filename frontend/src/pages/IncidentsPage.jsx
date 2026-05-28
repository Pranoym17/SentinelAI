import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { Button, DataTable, EmptyState, Panel, SkeletonRows, StatusBadge, TableHeader, TableRow } from '../components/ui.jsx';

export default function IncidentsPage() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState({ active: [], resolved: [] });
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getIncidents()
      .then(setIncidents)
      .catch((err) => {
        setError(err.message);
        setIncidents({ active: [], resolved: [] });
      })
      .finally(() => setLoading(false));
  }, []);

  const rows = [...(incidents.active || []), ...(incidents.resolved || [])].filter((incident) =>
    filter === 'all' ? true : incident.status === filter,
  );
  const total = (incidents.active?.length || 0) + (incidents.resolved?.length || 0);

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
        </div>
        <select value={filter} onChange={(event) => setFilter(event.target.value)}>
          <option value="all">All</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>
      {error && <div className="notice">{error}</div>}
      <Panel>
        {loading ? (
          <SkeletonRows rows={5} />
        ) : rows.length === 0 ? (
          total === 0 ? (
            <EmptyState title="◎ No incidents recorded" copy="The agent is monitoring your services. Incidents will appear here automatically when anomalies are detected." />
          ) : (
            <EmptyState
              title="◎ No incidents match your filters"
              copy="Adjust the status filter to see more incidents."
              action={<Button size="sm" variant="ghost" onClick={() => setFilter('all')}>Clear filters</Button>}
            />
          )
        ) : (
          <DataTable columns="86px 110px minmax(240px, 1fr) 86px 90px 140px">
            <TableHeader cells={['Severity', 'Service', 'Hypothesis', 'Status', 'Jira', 'Time']} />
            {rows.map((incident) => (
              <TableRow key={incident.id} onClick={() => navigate(`/incidents/${incident.id}`)}>
                <span><StatusBadge status={incident.severity} /></span>
                <span>{incident.service || '—'}</span>
                <span className="truncate" title={incident.hypothesis || ''}>{truncate(incident.hypothesis)}</span>
                <span>{incident.status}</span>
                <span>{incident.jira_ticket_id || '—'}</span>
                <span>{formatTime(incident.detected_at)}</span>
              </TableRow>
            ))}
          </DataTable>
        )}
      </Panel>
    </main>
  );
}

function truncate(value = '', limit = 60) {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value || '—';
}

function formatTime(value) {
  if (!value) return '—';
  const then = new Date(value).getTime();
  const minutes = Math.round((Date.now() - then) / 60000);
  if (Number.isFinite(minutes) && minutes < 60) return `${Math.max(0, minutes)} minutes ago`;
  if (Number.isFinite(minutes) && minutes < 1440) return `${Math.round(minutes / 60)} hours ago`;
  return new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric' });
}
