import { agentName, eventLabel, eventTone, formatDateTime } from './incidentStory.js';
import { Panel, SectionHeader, StatusBadge, StatusDot } from './ui.jsx';

export default function TimelineFeed({ timeline }) {
  const events = [...(timeline || [])].reverse().slice(0, 50);
  return (
    <Panel className="compact">
      <SectionHeader title="Agent timeline" meta={`${events.length} captured events`} />
      <div className="activity-list timeline-list">
        {events.length === 0 && (
          <div className="activity-empty-box">
            <StatusDot status="healthy" />
            <span>{'Monitoring active \u2014 waiting for first signal'}</span>
          </div>
        )}
        {events.map((event) => (
          <div className={`activity-item timeline-item ${eventTone(event)}`} key={event.id || `${event.event_type}-${event.occurred_at}`}>
            <time>{event.occurred_at ? formatDateTime(event.occurred_at) : 'Pending'}</time>
            <div className="timeline-kind">
              <StatusBadge status={eventTone(event)} />
              <b>{eventLabel(event.event_type)}</b>
            </div>
            <div>
              <strong>{agentName(event)}</strong>
              <span>{event.description || 'Agent event captured.'}</span>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
