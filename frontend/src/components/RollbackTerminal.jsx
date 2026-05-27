import { useState } from 'react';
import { Terminal } from 'lucide-react';
import { api } from '../api.js';
import { TerminalPanel } from './ui.jsx';
import { BlastGrid } from './IncidentCommandPanel.jsx';

export default function RollbackTerminal({ incident, busy, onRollback }) {
  const [blastRadius, setBlastRadius] = useState(null);
  const [checking, setChecking] = useState(false);
  const logs = (incident?.timeline || []).filter((event) => event.event_type === 'rollback_log');
  const completed = (incident?.timeline || []).some((event) => event.event_type === 'rollback_completed');

  async function prepareRollback() {
    if (!incident) return;
    setChecking(true);
    try {
      const data = await api.analyzeBlastRadius(incident.incident_id);
      setBlastRadius(data);
    } finally {
      setChecking(false);
    }
  }

  async function confirmRollback() {
    setBlastRadius(null);
    await onRollback();
  }

  return (
    <section className="panel compact-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Rollback</p>
          <h2>Mitigation log</h2>
        </div>
        <Terminal size={20} />
      </div>
      <button type="button" disabled={!incident || busy || checking || completed} onClick={prepareRollback}>
        {completed ? 'Rollback complete' : checking ? 'Checking blast radius...' : 'Run rollback'}
      </button>
      <TerminalPanel title="rollback.log" lines={logs.map((event) => event.description)} empty="waiting for rollback..." />
      {blastRadius && (
        <div className="modal-backdrop" role="dialog" aria-label="Confirm rollback">
          <div className="modal-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Blast radius check</p>
                <h2>{blastRadius.risk_level} rollback risk</h2>
              </div>
              <button type="button" className="ghost-button icon-button" onClick={() => setBlastRadius(null)}>
                x
              </button>
            </div>
            <p className="muted">{blastRadius.warning || 'No connected services found.'}</p>
            <BlastGrid blastRadius={blastRadius} />
            <div className="modal-actions">
              <button type="button" className="ghost-button" onClick={() => setBlastRadius(null)}>
                Cancel
              </button>
              <button type="button" className="danger-button" onClick={confirmRollback}>
                Confirm rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
