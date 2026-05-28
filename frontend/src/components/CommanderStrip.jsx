import { deriveStages, currentStage } from './incidentStory.js';
import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function CommanderStrip({ incident, timeline = [] }) {
  const events = incident?.timeline || timeline || [];
  const stages = deriveStages(incident, events);
  const active = currentStage(incident, events);
  const hasWork = Boolean(incident || events.length);

  if (!hasWork) {
    return (
      <Panel className="compact commander-panel">
        <SectionHeader title="Incident commander" meta="Lifecycle agents ready" />
        <EmptyState
          title="Agent lifecycle ready"
          copy="Detection, investigation, response, remediation, and post-mortem agents are standing by."
        />
      </Panel>
    );
  }

  return (
    <Panel className="compact commander-panel">
      <SectionHeader
        title="Incident commander"
        meta={active?.detail || 'Agent stages'}
        action={<StatusBadge status={active?.state || 'ready'} />}
      />
      <div className="commander-strip">
        {stages.map((stage) => (
          <div className={`commander-stage ${stage.state}`} key={stage.key}>
            <span className="commander-node">{symbolFor(stage.state)}</span>
            <div>
              <strong>{stage.label}</strong>
              <small>{stage.detail}</small>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function symbolFor(state) {
  if (state === 'completed') return '✓';
  if (state === 'failed') return '×';
  if (state === 'running') return '•';
  return '·';
}
