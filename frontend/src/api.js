async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || `Request failed: ${response.status}`);
  }
  return data;
}

export const api = {
  saveConfig: (config) =>
    request('/api/config', {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  getMetrics: () => request('/api/metrics'),
  getDeploys: () => request('/api/deploys'),
  createDeploy: (deploy) =>
    request('/api/deploys', {
      method: 'POST',
      body: JSON.stringify(deploy),
    }),
  getDemoState: () => request('/api/demo/state'),
  getIntegrationStatus: () => request('/api/integrations/status'),
  seedDemo: () => request('/api/seed/demo', { method: 'POST' }),
  seedDeploys: (deploys) =>
    request('/api/seed/deploys', {
      method: 'POST',
      body: JSON.stringify({ deploys }),
    }),
  seedMemory: (incidents) =>
    request('/api/seed/memory', {
      method: 'POST',
      body: JSON.stringify({ incidents }),
    }),
  injectSignal: (signal) =>
    request('/api/signal', {
      method: 'POST',
      body: JSON.stringify(signal),
    }),
  queryStatus: (query, incidentId) =>
    request('/api/status', {
      method: 'POST',
      body: JSON.stringify({ query, incident_id: incidentId }),
    }),
  resolveIncident: (incidentId, resolutionText) =>
    request(`/api/incidents/${incidentId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_text: resolutionText }),
    }),
  rollbackIncident: (incidentId, delaySeconds = 0) =>
    request(`/api/incidents/${incidentId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ delay_seconds: delaySeconds }),
    }),
};
