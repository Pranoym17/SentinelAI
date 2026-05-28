import { Button, Panel, SectionHeader } from './ui.jsx';

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

  if (!content) return null;

  return (
    <Panel>
      <SectionHeader title="Post-mortem" action={<Button size="sm" onClick={download}>Download markdown</Button>} />
      <pre className="markdown-preview">{content}</pre>
    </Panel>
  );
}
