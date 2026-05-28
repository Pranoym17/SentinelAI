import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { api } from '../api.js';
import { artifactBadges, durationText } from '../components/incidentStory.js';
import { Button, DataTable, EmptyState, Panel, SkeletonRows, StatusBadge, StatusDot, TableHeader, TableRow } from '../components/ui.jsx';

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

  const rows = [...(incidents.active || []), ...(incidents.resolved || [])]
    .filter((incident) => filter === 'all' ? true : incident.status === filter)
    .sort((a, b) => rankIncident(b) - rankIncident(a));
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
            <div className="incident-empty">
              <ShieldAlert size={58} strokeWidth={1.4} />
              <h2>No incidents detected</h2>
              <p>SentinelAI is actively monitoring your services. When an anomaly is detected, incidents will appear here with full timeline and actions.</p>
              <span className="watching-pill"><StatusDot status="healthy" /> Agent watching 3 services</span>
            </div>
          ) : (
            <EmptyState
              title="No incidents match your filters"
              copy="Adjust the status filter to see more incidents."
              action={<Button size="sm" variant="ghost" onClick={() => setFilter('all')}>Clear filters</Button>}
            />
          )
        ) : (
          <DataTable columns="86px 110px minmax(260px, 1fr) 86px 90px 150px 150px">
            <TableHeader cells={['Severity', 'Service', 'Hypothesis', 'Confidence', 'Status', 'Artifacts', 'Duration']} />
            {rows.map((incident) => (
              <TableRow key={incident.id} onClick={() => navigate(`/incidents/${incident.id}`)}>
                <span><StatusBadge status={incident.severity} /></span>
                <span>{incident.service || '-'}</span>
                <span className="truncate" title={incident.hypothesis || ''}>{truncate(incident.hypothesis)}</span>
                <span>{incident.confidence ?? 0}%</span>
                <span><StatusBadge status={incident.status} /></span>
                <span className="artifact-mini">{artifactBadges(incident).map(([label]) => label).join(', ') || 'Evidence pending'}</span>
                <span>{durationText(incident)}</span>
              </TableRow>
            ))}
          </DataTable>
        )}
      </Panel>
    </main>
  );
}

function truncate(value = '', limit = 60) {
  return value.length > limit ? `${value.slice(0, limit - 1)}...` : value || '-';
}

function formatTime(value) {
  if (!value) return '-';
  const then = new Date(value).getTime();
  const minutes = Math.round((Date.now() - then) / 60000);
  if (Number.isFinite(minutes) && minutes < 60) return `${Math.max(0, minutes)} minutes ago`;
  if (Number.isFinite(minutes) && minutes < 1440) return `${Math.round(minutes / 60)} hours ago`;
  return new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function rankIncident(incident) {
  const severity = { 'SEV-1': 40, 'SEV-2': 30, 'SEV-3': 20 };
  return (incident.status === 'open' ? 100 : 0) + (severity[incident.severity] || 0) + (incident.confidence || 0) / 100;
}
