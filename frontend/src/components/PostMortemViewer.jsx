import { Button, EmptyState, Panel, SectionHeader } from './ui.jsx';

export default function PostMortemViewer({ incident, markdown }) {
  const content = markdown || incident?.post_mortem || '';

  function download() {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sentinelai-incident-${incident?.incident_id || 'latest'}-post-mortem.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (!content) {
    return (
      <Panel>
        <SectionHeader title="Post-mortem" meta="Resolution record" />
        <EmptyState
          title="Post-mortem will be generated after resolution"
          copy="SentinelAI uses the captured timeline, actions, evidence, and resolution summary to create the incident record."
        />
      </Panel>
    );
  }

  return (
    <Panel>
      <SectionHeader title="Post-mortem" meta="Automatically generated incident record" action={<Button size="sm" onClick={download}>Download markdown</Button>} />
      <pre className="markdown-preview">{content}</pre>
    </Panel>
  );
}
