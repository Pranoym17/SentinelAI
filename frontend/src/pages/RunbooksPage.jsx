import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card } from '../components/ui.jsx';

export default function RunbooksPage() {
  const [runbooks, setRunbooks] = useState([]);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState({ service: 'payments', signal_type: 'error_spike', title: '', steps: '' });

  async function load() {
    const data = await api.getRunbooks();
    setRunbooks(data.runbooks || []);
  }

  useEffect(() => {
    load().catch(() => null);
  }, []);

  async function create() {
    if (!draft.title) return;
    await api.createRunbook({
      service: draft.service,
      signal_type: draft.signal_type,
      title: draft.title,
      steps: draft.steps.split('\n').map((step) => step.trim()).filter(Boolean),
    });
    setDraft({ service: 'payments', signal_type: 'error_spike', title: '', steps: '' });
    await load();
  }

  const filtered = runbooks.filter((runbook) => `${runbook.title} ${runbook.service}`.toLowerCase().includes(query.toLowerCase()));

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <p className="eyebrow">Memory</p>
          <h1>Runbooks</h1>
        </div>
        <input className="search-input" placeholder="Search runbooks" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      <div className="service-grid">
        {filtered.map((runbook) => (
          <Card key={runbook.id}>
            <p className="eyebrow">{runbook.service || 'global'} · {runbook.signal_type || 'any signal'}</p>
            <h2>{runbook.title}</h2>
            <ol className="steps-list">
              {(runbook.steps || []).map((step) => <li key={step}>{step}</li>)}
            </ol>
            <div className="mini-stats">
              <span>{runbook.times_used} used</span>
              <span>{runbook.success_rate}% success</span>
            </div>
          </Card>
        ))}
      </div>
      <Card>
        <p className="eyebrow">Create runbook</p>
        <div className="form-grid">
          <input value={draft.service} onChange={(event) => setDraft({ ...draft, service: event.target.value })} />
          <input value={draft.signal_type} onChange={(event) => setDraft({ ...draft, signal_type: event.target.value })} />
          <input placeholder="title" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
          <textarea placeholder="one step per line" value={draft.steps} onChange={(event) => setDraft({ ...draft, steps: event.target.value })} />
        </div>
        <button type="button" onClick={create}>Create runbook</button>
      </Card>
    </main>
  );
}
