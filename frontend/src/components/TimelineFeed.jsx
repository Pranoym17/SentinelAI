import { Panel, SectionHeader, StatusDot } from './ui.jsx';

export default function TimelineFeed({ timeline }) {
  const events = [...(timeline || [])].reverse().slice(0, 50);
  return (
    <Panel className="compact">
      <SectionHeader title="Activity feed" meta={`${events.length} events`} />
      <div className="activity-list">
        {events.length === 0 && (
          <div className="activity-empty-box">
            <StatusDot status="healthy" />
            <span>{'Monitoring active \u2014 waiting for first signal'}</span>
          </div>
        )}
        {events.map((event) => (
          <div className="activity-item" key={event.id || `${event.event_type}-${event.occurred_at}`}>
            <time>{event.occurred_at ? new Date(event.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</time>
            <b>{event.event_type}</b>
            <span>{event.description}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
