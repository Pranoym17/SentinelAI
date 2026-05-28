import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function TimelineFeed({ timeline }) {
  const events = [...(timeline || [])].reverse().slice(0, 50);
  return (
    <Panel className="compact">
      <SectionHeader title="Activity feed" meta={`${events.length} events`} />
      <div className="activity-list">
        {events.length === 0 && <EmptyState title="No activity" copy="Agent and integration events will appear here." />}
        {events.map((event) => (
          <div className="activity-item" key={event.id || `${event.event_type}-${event.occurred_at}`}>
            <time>{event.occurred_at ? new Date(event.occurred_at).toLocaleTimeString() : '--:--'}</time>
            <b>{event.event_type}</b>
            <span>{event.description}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
