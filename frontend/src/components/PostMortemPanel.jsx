export default function PostMortemPanel({ postMortem }) {
  return (
    <section className="panel">
      <p className="eyebrow">Post-Mortem</p>
      <pre className="markdown-preview">{postMortem}</pre>
    </section>
  );
}
