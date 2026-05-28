import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function IncidentHistory({ incidents, onSelect }) {
  const resolved = incidents?.resolved || [];
  return (
    <Panel className="compact">
      <SectionHeader title="Resolved incidents" meta={`${resolved.length} total`} />
      <div className="history-list">
        {resolved.length === 0 && <EmptyState title="No resolved incidents" copy="Resolved incidents appear after post-mortem generation." />}
        {resolved.slice(0, 8).map((incident) => (
          <button type="button" className="history-item" key={incident.id} onClick={() => onSelect(incident.id)}>
            <strong>{incident.service}</strong>
            <StatusBadge status={incident.severity} />
          </button>
        ))}
      </div>
    </Panel>
  );
}
