import { Activity, AlertTriangle, Terminal } from 'lucide-react';

export function Card({ children, className = '', glow = false }) {
  return <section className={`panel card ${glow ? 'panel-glow' : ''} ${className}`}>{children}</section>;
}

export function StatusDot({ status = 'normal' }) {
  return <span className={`status-dot-inline ${status}`} aria-hidden="true" />;
}

export function SeverityBadge({ severity = 'SEV-3' }) {
  return <span className={`severity-badge ${severity.toLowerCase().replace('-', '')}`}>{severity}</span>;
}

export function TerminalPanel({ title = 'Agent output', lines = [], empty = 'Waiting for signal...' }) {
  return (
    <div className="terminal-panel">
      <div className="terminal-head">
        <Terminal size={14} />
        <span>{title}</span>
      </div>
      <div className="terminal-body">
        {lines.length === 0 && <span className="terminal-muted">{empty}</span>}
        {lines.map((line, index) => (
          <div className="terminal-line" style={{ animationDelay: `${index * 90}ms` }} key={`${index}-${line.step || line}`}>
            {typeof line === 'object' ? (
              <>
                <strong>[{line.step}]</strong> {line.detail}
              </>
            ) : (
              <>$ {line}</>
            )}
          </div>
        ))}
        <span className="cursor">█</span>
      </div>
    </div>
  );
}

export function EmptyState({ title, copy }) {
  return (
    <div className="empty-state">
      <Activity size={24} />
      <strong>{title}</strong>
      <span>{copy}</span>
    </div>
  );
}

export function WarningBox({ children }) {
  return (
    <div className="warning-box">
      <AlertTriangle size={18} />
      <span>{children}</span>
    </div>
  );
}
