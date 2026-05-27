import { AlertTriangle, Zap } from 'lucide-react';

export default function SignalInjector({ onInject, loading }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Demo Controls</p>
          <h2>Inject monitoring signal</h2>
        </div>
        <Zap size={22} />
      </div>

      <div className="button-row">
        <button
          type="button"
          className="danger-button"
          disabled={loading}
          onClick={() =>
            onInject({
              service: 'payments',
              type: 'error_spike',
              value: 18,
              baseline: 0.2,
              unit: 'percent',
            })
          }
        >
          <AlertTriangle size={18} />
          {loading ? 'Agent investigating...' : 'Inject error spike'}
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() =>
            onInject({
              service: 'payments',
              type: 'latency_spike',
              value: 3500,
              baseline: 150,
              unit: 'ms',
            })
          }
        >
          Inject latency spike
        </button>
      </div>
    </section>
  );
}
