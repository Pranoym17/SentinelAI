function Dot({ ok }) {
  return <span className={`tiny-dot ${ok ? 'ok' : 'bad'}`} />;
}

export default function IntegrationStatus({ integrations }) {
  const items = [
    ['OpenAI', integrations?.openai?.configured, integrations?.openai?.model || 'fallback'],
    ['Jira', integrations?.jira?.configured, integrations?.jira?.project_key || 'not configured'],
    ['Slack', integrations?.slack?.configured, integrations?.slack?.channel || 'not configured'],
  ];

  return (
    <section className="panel compact-panel">
      <p className="eyebrow">Integrations</p>
      <div className="integration-list">
        {items.map(([name, ok, detail]) => (
          <div className="integration-row" key={name}>
            <Dot ok={ok} />
            <strong>{name}</strong>
            <span>{detail}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
