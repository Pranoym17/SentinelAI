export function Button({ children, variant = 'secondary', size = 'md', loading = false, disabled = false, className = '', ...props }) {
  return (
    <button
      className={`btn btn-${variant} btn-${size} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? '...' : children}
    </button>
  );
}

export function Panel({ children, className = '' }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export const Card = Panel;

export function SectionHeader({ title, meta, action }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {meta && <p>{meta}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatusBadge({ status = 'resolved' }) {
  return <span className={`status-badge ${statusClass(status)}`}>{status}</span>;
}

export function SeverityBadge({ severity = 'SEV-3' }) {
  return <StatusBadge status={severity} />;
}

export function StatusDot({ status = 'healthy' }) {
  return <span className={`status-dot ${statusClass(status)}`} aria-hidden="true" />;
}

export function MetricCell({ label, value, unit, status = 'neutral', sublabel }) {
  return (
    <div className={`metric-cell ${statusClass(status)}`}>
      <span>{label}</span>
      <strong>
        {value}
        {unit && <em>{unit}</em>}
      </strong>
      {sublabel && <small>{sublabel}</small>}
    </div>
  );
}

export function TerminalPanel({ title = 'sentinel', lines = [], height = 260, live = false, empty = '> waiting for events' }) {
  return (
    <div className="terminal-panel">
      <div className="terminal-title">
        <span>{title}</span>
        {live && <b>LIVE</b>}
      </div>
      <div className="terminal-body" style={{ minHeight: height }}>
        {lines.length === 0 && <span className="terminal-empty">{empty}</span>}
        {lines.map((line, index) => (
          <div className="terminal-line" style={{ animationDelay: `${index * 55}ms` }} key={`${index}-${line.step || line}`}>
            {typeof line === 'object' ? (
              <>
                <mark>[{line.step}]</mark>
                <span>{line.detail}</span>
                {line.confidence !== undefined && <i>{line.confidence}%</i>}
              </>
            ) : (
              <span>{line}</span>
            )}
          </div>
        ))}
        {live && <span className="terminal-cursor">_</span>}
      </div>
    </div>
  );
}

export function ConfidenceMeter({ value = 0 }) {
  const band = value >= 80 ? 'healthy' : value >= 50 ? 'warning' : 'critical';
  return (
    <div className="confidence-meter">
      <div>
        <span>Confidence</span>
        <strong className={band}>{value}%</strong>
      </div>
      <div className="meter-track">
        <span className={band} style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
      </div>
    </div>
  );
}

export function EmptyState({ title, copy, action }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <span>{copy}</span>
      {action}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }) {
  return (
    <div className="skeleton-stack">
      {Array.from({ length: rows }).map((_, index) => (
        <div className="skeleton-row" key={index} />
      ))}
    </div>
  );
}

export function DataTable({ columns, children }) {
  return (
    <div className="data-table" style={{ '--columns': columns }}>
      {children}
    </div>
  );
}

export function TableHeader({ cells }) {
  return (
    <div className="data-row data-head">
      {cells.map((cell) => <span key={cell}>{cell}</span>)}
    </div>
  );
}

export function TableRow({ children, onClick }) {
  const Component = onClick ? 'button' : 'div';
  return (
    <Component type={onClick ? 'button' : undefined} className="data-row" onClick={onClick}>
      {children}
    </Component>
  );
}

function statusClass(status) {
  const value = String(status || '').toLowerCase();
  if (value.includes('sev-1') || value.includes('critical') || value === 'open' || value.includes('breach')) return 'critical';
  if (value.includes('sev-2') || value.includes('warning') || value.includes('risk') || value.includes('degraded')) return 'warning';
  if (value.includes('sev-3') || value.includes('healthy') || value.includes('resolved') || value.includes('ok')) return 'healthy';
  return 'neutral';
}
