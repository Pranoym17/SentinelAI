export default function TimelineFeed({ timeline }) {
  return (
    <section className="panel compact-panel">
      <p className="eyebrow">Timeline</p>
      <ul className="timeline">
        {(timeline || []).map((event) => (
          <li key={event.id || `${event.event_type}-${event.occurred_at}`}>
            <span>{event.event_type}</span>
            {event.description}
          </li>
        ))}
      </ul>
    </section>
  );
}
