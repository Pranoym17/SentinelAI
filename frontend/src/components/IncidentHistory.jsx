export default function IncidentHistory({ incidents, onSelect }) {
  const resolved = incidents?.resolved || [];
  return (
    <section className="panel compact-panel">
      <p className="eyebrow">Incident History</p>
      <div className="history-list">
        {resolved.length === 0 && <p className="muted">No resolved incidents yet.</p>}
        {resolved.map((incident) => (
          <button
            type="button"
            className="history-item"
            key={incident.id}
            onClick={() => onSelect(incident.id)}
          >
            <strong>{incident.service}</strong>
            <span>{incident.severity}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
