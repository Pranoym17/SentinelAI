export default function TimelineFeed({ timeline }) {
  const importantEvents = new Set([
    'oncall_identified',
    'sla_warning',
    'runbook_success_recorded',
    'correlation_detected',
    'blast_radius_analyzed',
  ]);

  return (
    <section className="panel compact-panel">
      <p className="eyebrow">Timeline</p>
      <ul className="timeline">
        {(timeline || []).map((event) => (
          <li
            className={importantEvents.has(event.event_type) ? 'timeline-important' : ''}
            key={event.id || `${event.event_type}-${event.occurred_at}`}
          >
            <span>{event.event_type}</span>
            {event.description}
          </li>
        ))}
      </ul>
    </section>
  );
}
