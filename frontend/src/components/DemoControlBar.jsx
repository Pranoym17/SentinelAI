import { RotateCcw, Siren, Sparkles, Zap } from 'lucide-react';

export default function DemoControlBar({ busy, onFullSeed, onReset, onTrigger, onInject }) {
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
        Start autonomous demo
      </button>
      <button type="button" className="danger-button" disabled={busy} onClick={onInject}>
        <Zap size={18} />
        Inject spike
      </button>
    </section>
  );
}
