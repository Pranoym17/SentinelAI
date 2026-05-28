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
  getIntegrations: () => request('/api/integrations'),
  saveIntegration: (integration) =>
    request('/api/integrations', {
      method: 'POST',
      body: JSON.stringify(integration),
    }),
  testIntegration: (type) => request(`/api/integrations/${type}/test`, { method: 'POST' }),
  getServices: () => request('/api/services'),
  createService: (service) =>
    request('/api/services', {
      method: 'POST',
      body: JSON.stringify(service),
    }),
  getSla: () => request('/api/sla'),
  getCurrentOncall: () => request('/api/oncall/current'),
  createOncall: (schedule) =>
    request('/api/oncall', {
      method: 'POST',
      body: JSON.stringify(schedule),
    }),
  getRunbooks: () => request('/api/runbooks'),
  createRunbook: (runbook) =>
    request('/api/runbooks', {
      method: 'POST',
      body: JSON.stringify(runbook),
    }),
  getAnalytics: () => request('/api/analytics'),
  getIncidents: () => request('/api/incidents'),
  getIncident: (incidentId) => request(`/api/incidents/${incidentId}`),
  getMetricHistory: (limit = 120) => request(`/api/metrics/history?limit=${limit}`),
  fullSeed: () => request('/api/demo/full-seed', { method: 'POST' }),
  resetDemo: (keepConfig = true) =>
    request(`/api/demo/reset?keep_config=${keepConfig ? 'true' : 'false'}`, { method: 'POST' }),
  triggerDemo: (delaySeconds = 30) =>
    request(`/api/demo/trigger?delay_seconds=${delaySeconds}`, { method: 'POST' }),
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
  analyzeBlastRadius: (incidentId) =>
    request(`/api/incidents/${incidentId}/blast-radius`, {
      method: 'POST',
    }),
  generateFixPreview: (incidentId) =>
    request(`/api/incidents/${incidentId}/fix-preview`, {
      method: 'POST',
    }),
  createGithubPr: (incidentId) =>
    request(`/api/incidents/${incidentId}/github-pr`, {
      method: 'POST',
    }),
};
