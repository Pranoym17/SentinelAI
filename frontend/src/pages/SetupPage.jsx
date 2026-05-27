import { useNavigate } from 'react-router-dom';

export default function SetupPage() {
  const navigate = useNavigate();

  return (
    <main className="page">
      <section className="panel">
        <p className="eyebrow">SentinelAI</p>
        <h1>Incident agent setup</h1>
        <p className="muted">
          Backend and frontend scaffolds are ready. Configuration controls come next.
        </p>
        <button type="button" onClick={() => navigate('/dashboard')}>
          Open dashboard
        </button>
      </section>
    </main>
  );
}
