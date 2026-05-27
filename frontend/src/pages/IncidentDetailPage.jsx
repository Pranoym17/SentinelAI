import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api.js';
import IncidentCommandPanel from '../components/IncidentCommandPanel.jsx';
import TimelineFeed from '../components/TimelineFeed.jsx';
import PostMortemViewer from '../components/PostMortemViewer.jsx';
import { Card, EmptyState } from '../components/ui.jsx';

export default function IncidentDetailPage() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [postMortem, setPostMortem] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.getIncident(id);
      setIncident(data);
      setPostMortem(data.post_mortem || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  return (
    <main className="page-shell">
      <div className="page-head">
        <div>
          <p className="eyebrow">Incident detail</p>
          <h1>{incident ? `${incident.severity}: ${incident.service}` : 'Loading incident'}</h1>
        </div>
      </div>
      {error && <div className="notice">{error}</div>}
      {loading && <Card><EmptyState title="Loading incident" copy="Fetching incident detail and timeline." /></Card>}
      <div className="dashboard-grid">
        <section className="main-stack">
          <IncidentCommandPanel incident={incident} onRefresh={load} onResolved={setPostMortem} />
          <PostMortemViewer incident={incident} markdown={postMortem} />
        </section>
        <aside className="right-rail">
          <TimelineFeed timeline={incident?.timeline || []} />
        </aside>
      </div>
    </main>
  );
}
