import { RotateCcw, Siren, Sparkles, Zap } from 'lucide-react';

export default function DemoControlBar({ busy, countdown, workerState, onFullSeed, onReset, onTrigger, onInject }) {
  return (
    <section className="panel control-bar">
      <button type="button" disabled={busy} onClick={onFullSeed}>
        <Sparkles size={18} />
        Full seed
      </button>
      <button type="button" disabled={busy} onClick={onReset}>
        <RotateCcw size={18} />
        Reset
      </button>
      <button type="button" disabled={busy} onClick={onTrigger}>
        <Siren size={18} />
        {countdown ? `Auto-detect in ${countdown}s` : 'Start autonomous demo'}
      </button>
      <button type="button" className="danger-button" disabled={busy} onClick={onInject}>
        <Zap size={18} />
        Inject spike
      </button>
      <div className={`autonomy-indicator ${workerState?.incident_active ? 'active' : ''}`}>
        <span className="status-dot-inline critical" />
        {workerState?.payment_spike_at ? 'Autonomous trigger armed' : workerState?.incident_active ? 'Incident active' : 'Agent watching'}
      </div>
    </section>
  );
}
