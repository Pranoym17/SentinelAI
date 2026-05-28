import { useState } from 'react';

import { api } from '../api.js';
import { BlastGrid } from './IncidentCommandPanel.jsx';
import { Button, Panel, SectionHeader, StatusBadge, TerminalPanel } from './ui.jsx';

export default function RollbackTerminal({ incident, busy, onRollback }) {
  const [blastRadius, setBlastRadius] = useState(null);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');
  const logs = (incident?.timeline || []).filter((event) => event.event_type === 'rollback_log');
  const completed = (incident?.timeline || []).some((event) => event.event_type === 'rollback_completed');

  async function prepareRollback() {
    if (!incident) return;
    setChecking(true);
    setMessage('');
    try {
      const data = await api.analyzeBlastRadius(incident.incident_id);
      setBlastRadius(data);
      setMessage('Blast radius simulation completed. Human confirmation is required before rollback.');
    } catch (err) {
      setMessage(err.message);
    } finally {
      setChecking(false);
    }
  }

  async function confirmRollback() {
    setBlastRadius(null);
    await onRollback();
  }

  return (
    <Panel className="compact">
      <SectionHeader
        title="Rollback"
        meta={completed ? 'remediation completed' : incident ? 'blast radius gated remediation' : 'waiting for incident'}
        action={
          <Button size="sm" variant="danger" disabled={!incident || busy || checking || completed} onClick={prepareRollback}>
            {completed ? 'Complete' : checking ? 'Checking' : 'Run rollback'}
          </Button>
        }
      />
      <div className="remediation-summary">
        <StatusBadge status={completed ? 'healthy' : incident ? 'warning' : 'neutral'} />
        <span>{completed ? 'Rollback completed and captured in the incident timeline.' : incident ? 'Rollback requires blast-radius review and human confirmation.' : 'Rollback controls appear when an incident is active.'}</span>
      </div>
      <TerminalPanel title="rollback.log" lines={logs.map((event) => event.description)} height={160} empty="> waiting for rollback" />
      {message && <div className={message.includes('completed') ? 'notice success' : 'notice'}>{message}</div>}
      {blastRadius && (
        <div className="modal-backdrop" role="dialog" aria-label="Confirm rollback">
          <div className="modal-panel">
            <SectionHeader title={`${blastRadius.risk_level} rollback risk`} meta={blastRadius.warning || 'No connected services found.'} />
            <BlastGrid blastRadius={blastRadius} />
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setBlastRadius(null)}>Cancel</Button>
              <Button variant="danger" onClick={confirmRollback}>Confirm rollback</Button>
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}
