import { EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

const STAGES = [
  { agent: 'DetectionAgent', label: 'Detect' },
  { agent: 'InvestigatorAgent', label: 'Investigate' },
  { agent: 'ResponseAgent', label: 'Coordinate' },
  { agent: 'GitHubFixAgent', label: 'Fix' },
  { agent: 'RollbackAgent', label: 'Rollback' },
  { agent: 'PostMortemAgent', label: 'Post-mortem' },
];

export default function CommanderStrip({ timeline = [] }) {
  const agentEvents = timeline.filter((event) => event.metadata?.agent);
  const latest = [...agentEvents].reverse()[0];

  if (agentEvents.length === 0) {
    return (
      <Panel className="compact">
        <SectionHeader title="Incident commander" meta="Agent stages" />
        <EmptyState
          title="◎ Agent timeline ready"
          copy="Investigation stages will appear here when the next incident starts."
        />
      </Panel>
    );
  }

  return (
    <Panel className="compact commander-panel">
      <SectionHeader
        title="Incident commander"
        meta={latest ? latest.description : 'Agent stages'}
        action={<StatusBadge status={latest?.metadata?.status || 'ready'} />}
      />
      <div className="commander-strip">
        {STAGES.map((stage) => {
          const events = agentEvents.filter((event) => event.metadata?.agent === stage.agent);
          const last = events[events.length - 1];
          const state = stateFor(last);
          return (
            <div className={`commander-stage ${state}`} key={stage.agent}>
              <span className="commander-node">{symbolFor(state)}</span>
              <div>
                <strong>{stage.label}</strong>
                <small>{last ? shortDescription(last.description, stage.agent) : 'Waiting'}</small>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function stateFor(event) {
  if (!event) return 'pending';
  if (event.event_type === 'agent_failed') return 'failed';
  if (event.event_type === 'agent_completed') return 'completed';
  return 'active';
}

function symbolFor(state) {
  if (state === 'completed') return '✓';
  if (state === 'failed') return '×';
  if (state === 'active') return '→';
  return '·';
}

function shortDescription(description = '', agent) {
  return description.replace(`${agent}: `, '').slice(0, 76);
}
