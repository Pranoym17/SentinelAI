import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';

const steps = ['Services', 'Monitoring', 'Alerts', 'Ticketing', 'Launch'];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    services: [
      { name: 'payments', display_name: 'Payments API', team: 'payments-team', sla_target: 99.9 },
      { name: 'auth', display_name: 'Auth Service', team: 'auth-team', sla_target: 99.9 },
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
      <section className="onboarding-card">
        <div className="step-track">
          {steps.map((label, index) => (
            <button
              type="button"
              className={index === step ? 'active' : ''}
              key={label}
              onClick={() => setStep(index)}
            >
              {label}
            </button>
          ))}
        </div>

        {step === 0 && <ServicesStep form={form} setForm={setForm} />}
        {step === 1 && <ChoiceStep title="Monitoring" copy="Use the built-in simulator for demo, then connect Datadog or CloudWatch later." />}
        {step === 2 && (
          <FieldStep
            title="Alerts"
            fields={[['slack_channel', 'Slack channel']]}
            form={form}
            setForm={setForm}
          />
        )}
        {step === 3 && (
          <FieldStep
            title="Ticketing"
            fields={[['jira_project_key', 'Jira project key']]}
            form={form}
            setForm={setForm}
          />
        )}
        {step === 4 && <ChoiceStep title="Launch" copy="Configuration is ready. Seed demo data and open the command center." />}

        <div className="wizard-actions">
          <button type="button" className="ghost-button" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>
            Back
          </button>
          {step < steps.length - 1 ? (
            <button type="button" disabled={busy} onClick={() => setStep(step + 1)}>
              Continue
            </button>
          ) : (
            <button type="button" disabled={busy} onClick={finish}>
              {busy ? 'Launching...' : 'Launch SentinelAI'}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}

function ServicesStep({ form, setForm }) {
  const [draft, setDraft] = useState({ name: '', display_name: '', team: '', sla_target: 99.9 });
  return (
    <>
      <p className="eyebrow">Step 1</p>
      <h1>Services to monitor</h1>
      <div className="service-list">
        {form.services.map((service) => (
          <div className="service-row" key={service.name}>
            <strong>{service.display_name || service.name}</strong>
            <span>{service.team || 'No team'} · {service.sla_target}% SLA</span>
          </div>
        ))}
      </div>
      <div className="form-grid">
        <input placeholder="service-name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <input placeholder="Display name" value={draft.display_name} onChange={(event) => setDraft({ ...draft, display_name: event.target.value })} />
      </div>
      <button
        type="button"
        className="ghost-button"
        onClick={() => {
          if (!draft.name) return;
          setForm({ ...form, services: [...form.services, draft] });
          setDraft({ name: '', display_name: '', team: '', sla_target: 99.9 });
        }}
      >
        Add service
      </button>
    </>
  );
}

function ChoiceStep({ title, copy }) {
  return (
    <>
      <p className="eyebrow">Configuration</p>
      <h1>{title}</h1>
      <p className="muted">{copy}</p>
      <div className="choice-grid">
        <div>Built-in simulator</div>
        <div>Real Slack/Jira via backend env or saved DB config</div>
      </div>
    </>
  );
}

function FieldStep({ title, fields, form, setForm }) {
  return (
    <>
      <p className="eyebrow">Configuration</p>
      <h1>{title}</h1>
      <div className="form-grid">
        {fields.map(([key, label]) => (
          <label className="field" key={key}>
            {label}
            <input value={form[key] || ''} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />
          </label>
        ))}
      </div>
    </>
  );
}
