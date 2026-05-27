import { useNavigate } from 'react-router-dom';
import { ArrowRight, Gauge, MessageSquare, TicketCheck } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  return (
    <main className="landing">
      <div className="landing-inner">
        <p className="landing-badge">Autonomous AI incident response</p>
        <h1>SentinelAI</h1>
        <p className="landing-copy">
          Detect anomalies, investigate root cause, coordinate Jira and Slack, run rollback support, and generate
          post-mortems from the live incident timeline.
        </p>
        <div className="landing-actions">
          <button type="button" onClick={() => navigate('/onboarding')}>
            Start setup
            <ArrowRight size={18} />
          </button>
          <button type="button" className="ghost-button" onClick={() => navigate('/dashboard')}>
            Open dashboard
          </button>
        </div>
        <div className="feature-row">
          <span>
            <Gauge size={16} />
            SLA aware
          </span>
          <span>
            <MessageSquare size={16} />
            Slack ready
          </span>
          <span>
            <TicketCheck size={16} />
            Jira ready
          </span>
        </div>
      </div>
    </main>
  );
}
