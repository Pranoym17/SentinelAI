import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api.js';
import { Button, Panel, SectionHeader } from '../components/ui.jsx';

const steps = ['Services', 'Monitoring', 'Alerts', 'Ticketing', 'Launch'];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    services: [
      { name: 'payments', display_name: 'Payments API', team: 'payments-team', sla_target: 99.9 },
      { name: 'auth', display_name: 'Auth Service', team: 'auth-team', sla_target: 99.9 },
      { name: 'api-gateway', display_name: 'API Gateway', team: 'platform', sla_target: 99.9 },
    ],
    slack_channel: '#incidents',
    jira_project_key: 'SCRUM',
  });

  async function finish() {
    setBusy(true);
    try {
      await api.saveConfig({
        services: form.services.map((service) => service.name),
        signals: ['error_spike', 'latency_spike'],
        actions: ['jira', 'slack'],
        thresholds: { error_rate: 5, latency_ms: 2000, deployment_window_minutes: 60 },
        slack_channel: form.slack_channel,
        jira_project_key: form.jira_project_key,
      });
      for (const service of form.services) {
        await api.createService(service).catch(() => null);
      }
      await api.fullSeed();
      navigate('/dashboard');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="onboarding">
      <Panel className="onboarding-card">
        <div className="step-track">
          {steps.map((label, index) => <span className={index <= step ? 'active' : ''} key={label} />)}
        </div>
        <SectionHeader title={steps[step]} meta={`Step ${step + 1} of ${steps.length}`} />

        {step === 0 && <ServicesStep form={form} setForm={setForm} />}
        {step === 1 && <ChoiceStep copy="Simulation mode is selected. Datadog and CloudWatch can be wired later." />}
        {step === 2 && <FieldStep fields={[['slack_channel', 'Slack channel']]} form={form} setForm={setForm} />}
        {step === 3 && <FieldStep fields={[['jira_project_key', 'Jira project key']]} form={form} setForm={setForm} />}
        {step === 4 && <ChoiceStep copy="Configuration is ready. Launch seeds demo data and opens the dashboard." />}

        <div className="button-row" style={{ justifyContent: 'space-between', marginTop: 18 }}>
          <Button variant="secondary" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>Back</Button>
          {step < steps.length - 1 ? (
            <Button onClick={() => setStep(step + 1)} disabled={busy}>Continue</Button>
          ) : (
            <Button variant="primary" onClick={finish} disabled={busy}>{busy ? 'Launching' : 'Launch'}</Button>
          )}
        </div>
      </Panel>
    </main>
  );
}

function ServicesStep({ form, setForm }) {
  const [draft, setDraft] = useState({ name: '', display_name: '', team: '', sla_target: 99.9 });
  return (
    <div className="stack">
      <div className="service-list">
        {form.services.map((service) => (
          <div className="deploy-item" key={service.name}>
            <strong>{service.display_name || service.name}</strong>
            <small>{service.team || 'No team'} / {service.sla_target}% SLA</small>
          </div>
        ))}
      </div>
      <div className="form-grid">
        <input placeholder="service-name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <input placeholder="Display name" value={draft.display_name} onChange={(event) => setDraft({ ...draft, display_name: event.target.value })} />
      </div>
      <Button
        variant="secondary"
        onClick={() => {
          if (!draft.name) return;
          setForm({ ...form, services: [...form.services, draft] });
          setDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
        }}
      >
        Add service
      </Button>
    </div>
  );
}

function ChoiceStep({ copy }) {
  return (
    <div className="stack">
      <p className="muted">{copy}</p>
      <div className="info-grid">
        <div className="info-box"><strong>Simulation</strong><span>Built-in worker</span></div>
        <div className="info-box"><strong>Integrations</strong><span>Slack, Jira, GitHub</span></div>
      </div>
    </div>
  );
}

function FieldStep({ fields, form, setForm }) {
  return (
    <div className="form-grid">
      {fields.map(([key, label]) => (
        <label className="field" key={key}>
          {label}
          <input value={form[key] || ''} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />
        </label>
      ))}
    </div>
  );
}
