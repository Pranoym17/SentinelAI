import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { DataTable, EmptyState, Panel, StatusBadge, TableHeader, TableRow } from '../components/ui.jsx';

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
          <EmptyState title="Loading incidents" copy="Fetching active and resolved incidents." />
        ) : rows.length === 0 ? (
          <EmptyState title="No incidents yet" copy="Trigger the demo from the dashboard to populate this table." />
        ) : (
          <DataTable columns="86px 110px minmax(240px, 1fr) 86px 90px 140px">
            <TableHeader cells={['Severity', 'Service', 'Hypothesis', 'Status', 'Jira', 'Time']} />
            {rows.map((incident) => (
              <TableRow key={incident.id} onClick={() => navigate(`/incidents/${incident.id}`)}>
                <span><StatusBadge status={incident.severity} /></span>
                <span>{incident.service}</span>
                <span>{incident.hypothesis}</span>
                <span>{incident.status}</span>
                <span>{incident.jira_ticket_id || 'none'}</span>
                <span>{new Date(incident.detected_at).toLocaleString()}</span>
              </TableRow>
            ))}
          </DataTable>
        )}
      </Panel>
    </main>
  );
}
