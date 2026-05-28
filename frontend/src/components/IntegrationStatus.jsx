import { Panel, SectionHeader, StatusDot } from './ui.jsx';

export default function IntegrationStatus({ integrations }) {
  const items = [
    ['OpenAI', integrations?.openai?.configured, integrations?.openai?.model || 'fallback'],
    ['Jira', integrations?.jira?.configured, integrations?.jira?.project_key || 'not configured'],
    ['Slack', integrations?.slack?.configured, integrations?.slack?.channel || 'not configured'],
    ['GitHub', integrations?.github?.configured, integrations?.github?.configured ? 'configured' : 'not configured'],
  ];

  return (
    <Panel className="compact">
      <SectionHeader title="Integrations" />
      <div className="integration-list">
        {items.map(([name, ok, detail]) => (
          <div className="integration-row" key={name}>
            <StatusDot status={ok ? 'healthy' : 'critical'} />
            <strong>{name}</strong>
            <span>{detail}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
