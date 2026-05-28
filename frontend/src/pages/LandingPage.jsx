import { useEffect, useMemo, useState } from 'react';
import { BarChart3, BookOpen, CircleDot, Play, Rocket, RotateCcw, TriangleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Button, TerminalPanel } from '../components/ui.jsx';

const previewSteps = [
  { step: 'SIGNAL', detail: 'payments error_rate 0.2 -> 18.0', confidence: 30 },
  { step: 'MEMORY', detail: 'matched previous deploy regression', confidence: 55 },
  { step: 'DEPLOY', detail: 'payments-api v2.4.1 deployed 14m ago', confidence: 80 },
  { step: 'COMMIT', detail: 'a3f92c1 touched payments/sdk.py', confidence: 87 },
  { step: 'ACTION', detail: 'jira created, slack posted, rollback ready', confidence: 95 },
];

const features = [
  { label: 'anomaly detection', icon: CircleDot },
  { label: 'SLA aware routing', icon: TriangleAlert },
  { label: 'incident memory', icon: BookOpen },
  { label: 'runbook generation', icon: CircleDot },
  { label: 'rollback support', icon: RotateCcw },
  { label: 'analytics', icon: BarChart3 },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [count, setCount] = useState(1);
  const lines = useMemo(() => previewSteps.slice(0, count), [count]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setCount((current) => (current >= previewSteps.length ? 1 : current + 1));
    }, 1500);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <main className="landing">
      <section className="landing-copy">
        <h1><span>Autonomous</span> incident response</h1>
        <p>
          SentinelAI watches production signals, investigates likely cause, coordinates Jira and Slack, and writes the
          incident record while engineers focus on the fix.
        </p>
        <div className="button-row">
          <Button icon={Rocket} variant="primary" size="lg" onClick={() => navigate('/onboarding')}>Get started</Button>
          <Button icon={Play} variant="secondary" size="lg" onClick={() => navigate('/dashboard')}>View dashboard</Button>
        </div>
        <div className="feature-list">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <span key={feature.label}>
                <Icon size={13} strokeWidth={1.9} />
                {feature.label}
              </span>
            );
          })}
        </div>
      </section>
      <aside className="landing-terminal">
        <TerminalPanel title="preview" lines={lines} live height={420} />
      </aside>
    </main>
  );
}
