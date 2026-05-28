import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Button, EmptyState, Panel, SectionHeader, SkeletonRows } from '../components/ui.jsx';

export default function RunbooksPage() {
  const [runbooks, setRunbooks] = useState([]);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState({ service: 'payments', signal_type: 'error_spike', title: '', steps: '' });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.getRunbooks();
      setRunbooks(data.runbooks || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!draft.title) return;
    setBusy(true);
    setError('');
    try {
      await api.createRunbook({
        service: draft.service,
        signal_type: draft.signal_type,
        title: draft.title,
        steps: draft.steps.split('\n').map((step) => step.trim()).filter(Boolean),
      });
      setDraft({ service: 'payments', signal_type: 'error_spike', title: '', steps: '' });
      setMessage('Runbook created');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const filtered = runbooks.filter((runbook) =>
    `${runbook.title} ${runbook.service}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <h1>Runbooks</h1>
        </div>
        <input className="search-input" placeholder="Search runbooks" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      {message && <div className="notice success">{message}</div>}
      {error && <div className="notice">{error}</div>}
      {loading && <Panel><SkeletonRows rows={6} /></Panel>}
      <div className="card-grid three">
        {!loading && filtered.length === 0 && (
          <Panel><EmptyState title="≡ No runbooks yet" copy="Runbooks are generated automatically when incidents resolve. Your first runbook will appear here after your first incident." /></Panel>
        )}
        {filtered.map((runbook) => (
          <Panel key={runbook.id}>
            <span className="label">{runbook.service || 'global'} / {runbook.signal_type || 'any signal'}</span>
            <h2>{runbook.title}</h2>
            <ol className="steps-list">
              {(runbook.steps || []).map((step) => <li key={step}>{step}</li>)}
            </ol>
            <div className="runbook-stat-pills">
              <span>{runbook.times_used} uses</span>
              <span>{runbook.success_rate}% success</span>
            </div>
          </Panel>
        ))}
      </div>
      <Panel>
        <SectionHeader title="Create runbook" />
        <div className="form-grid">
          <label className="field">
            <span>Service</span>
            <input value={draft.service} onChange={(event) => setDraft({ ...draft, service: event.target.value })} />
          </label>
          <label className="field">
            <span>Signal type</span>
            <input value={draft.signal_type} onChange={(event) => setDraft({ ...draft, signal_type: event.target.value })} />
          </label>
          <label className="field">
            <span>Title</span>
            <input placeholder="title" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
          </label>
          <label className="field">
            <span>Steps</span>
            <textarea placeholder="one step per line" value={draft.steps} onChange={(event) => setDraft({ ...draft, steps: event.target.value })} />
          </label>
        </div>
        <Button variant="primary" disabled={busy || !draft.title.trim()} onClick={create}>
          {busy ? 'Creating...' : 'Create runbook'}
        </Button>
      </Panel>
    </main>
  );
}
