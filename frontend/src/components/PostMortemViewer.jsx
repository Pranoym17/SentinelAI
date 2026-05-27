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
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Post-Mortem</p>
          <h2>Generated report</h2>
        </div>
        <button type="button" onClick={download}>
          Download markdown
        </button>
      </div>
      <pre className="markdown-preview">{content}</pre>
    </section>
  );
}
