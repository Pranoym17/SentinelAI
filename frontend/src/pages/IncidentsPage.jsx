import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { Card, EmptyState, SeverityBadge } from '../components/ui.jsx';

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
          <p className="eyebrow">Operations</p>
          <h1>Incidents</h1>
        </div>
        <select value={filter} onChange={(event) => setFilter(event.target.value)}>
          <option value="all">All</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>
      {error && <div className="notice">{error}</div>}
      <Card>
        {loading ? (
          <EmptyState title="Loading incidents" copy="Fetching active and resolved incidents." />
        ) : rows.length === 0 ? (
          <EmptyState title="No incidents yet" copy="Trigger the demo from the dashboard to populate this table." />
        ) : (
          <div className="data-table">
            <div className="table-row table-head">
              <span>Severity</span>
              <span>Service</span>
              <span>Hypothesis</span>
              <span>Status</span>
              <span>Jira</span>
            </div>
            {rows.map((incident) => (
              <button className="table-row" type="button" key={incident.id} onClick={() => navigate(`/incidents/${incident.id}`)}>
                <span><SeverityBadge severity={incident.severity} /></span>
                <span>{incident.service}</span>
                <span>{incident.hypothesis}</span>
                <span>{incident.status}</span>
                <span>{incident.jira_ticket_id || 'none'}</span>
              </button>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
