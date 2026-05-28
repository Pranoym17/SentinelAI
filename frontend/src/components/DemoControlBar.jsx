import { Button, Panel } from './ui.jsx';

export default function DemoControlBar({ busy, countdown, workerState, onFullSeed, onReset, onTrigger, onInject }) {
  const stateText = workerState?.payment_spike_at
    ? 'Autonomous trigger armed'
    : workerState?.incident_active
      ? 'Incident active'
      : 'Agent watching';

  return (
    <Panel className="compact">
      <div className="action-row">
        <Button disabled={busy} onClick={onFullSeed}>Full seed</Button>
        <Button disabled={busy} onClick={onReset}>Reset</Button>
        <Button disabled={busy} onClick={onTrigger}>
          {countdown ? `Auto-detect in ${countdown}s` : 'Start autonomous demo'}
        </Button>
        <Button variant="danger" disabled={busy} onClick={onInject}>Inject spike</Button>
        <span className="label" style={{ alignSelf: 'center', marginLeft: 'auto' }}>
          {stateText}
        </span>
      </div>
    </Panel>
  );
}
