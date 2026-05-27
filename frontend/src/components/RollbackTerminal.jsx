import { Terminal } from 'lucide-react';
import { TerminalPanel } from './ui.jsx';

export default function RollbackTerminal({ incident, busy, onRollback }) {
  const logs = (incident?.timeline || []).filter((event) => event.event_type === 'rollback_log');
  const completed = (incident?.timeline || []).some((event) => event.event_type === 'rollback_completed');

  return (
    <section className="panel compact-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Rollback</p>
          <h2>Mitigation log</h2>
        </div>
        <Terminal size={20} />
      </div>
      <button type="button" disabled={!incident || busy || completed} onClick={onRollback}>
        {completed ? 'Rollback complete' : 'Run rollback'}
      </button>
      <TerminalPanel title="rollback.log" lines={logs.map((event) => event.description)} empty="waiting for rollback..." />
    </section>
  );
}
