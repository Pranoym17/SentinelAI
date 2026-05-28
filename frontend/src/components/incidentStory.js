export const COMMANDER_STAGES = [
  { key: 'detection', label: 'Detection' },
  { key: 'investigation', label: 'Investigation' },
  { key: 'response', label: 'Response' },
  { key: 'fix', label: 'Fix preview' },
  { key: 'github_pr', label: 'GitHub PR' },
  { key: 'post_mortem', label: 'Post-mortem' },
];

const AGENT_STAGE = {
  DetectionAgent: 'detection',
  InvestigatorAgent: 'investigation',
  ResponseAgent: 'response',
  GitHubFixAgent: 'fix',
  RollbackAgent: 'response',
  PostMortemAgent: 'post_mortem',
};

export function formatDateTime(value) {
  if (!value) return 'Pending';
  return new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function eventLabel(type = '') {
  return String(type)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function latestEvent(timeline = [], type) {
  return [...timeline].reverse().find((event) => event.event_type === type);
}

export function agentName(event) {
  return event?.metadata?.agent || event?.metadata?.actor || 'SentinelAI';
}

export function eventTone(event) {
  const type = event?.event_type || '';
  if (type.includes('failed') || event?.metadata?.status === 'failed') return 'critical';
  if (type.includes('warning') || type.includes('risk')) return 'warning';
  if (type.includes('created') || type.includes('completed') || type.includes('resolved') || type.includes('generated')) return 'healthy';
  return 'neutral';
}

export function deriveStages(incident, timelineInput = []) {
  const timeline = incident?.timeline || timelineInput || [];
  const completed = {
    detection: Boolean(incident) || hasEvent(timeline, /detection|signal|anomaly/),
    investigation: Boolean(incident?.hypothesis || (incident?.reasoning_chain || []).length) || hasEvent(timeline, /investigation|correlation|root_cause/),
    response: Boolean(incident?.jira_ticket_id || incident?.slack_message_ts) || hasEvent(timeline, /jira|slack|oncall|response|rollback_completed/),
    fix: Boolean(incident?.fix_preview) || hasEvent(timeline, /github_fix_preview_generated/),
    github_pr: Boolean(incident?.github_pr) || hasEvent(timeline, /github_pr_created/),
    post_mortem: Boolean(incident?.post_mortem) || hasEvent(timeline, /post_mortem/),
  };
  const failed = {
    detection: failedFor(timeline, 'detection'),
    investigation: failedFor(timeline, 'investigation'),
    response: failedFor(timeline, 'response') || hasEvent(timeline, /jira_.*failed|slack_.*failed|rollback_.*failed/),
    fix: failedFor(timeline, 'fix') || hasEvent(timeline, /github_branch_failed|github_file_failed|github_commit_failed/),
    github_pr: hasEvent(timeline, /github_pr_failed/),
    post_mortem: failedFor(timeline, 'post_mortem'),
  };
  const runningStage = stageFor([...timeline].reverse().find((event) => event.event_type === 'agent_started'));
  const nextIndex = COMMANDER_STAGES.findIndex((stage) => !completed[stage.key] && !failed[stage.key]);

  return COMMANDER_STAGES.map((stage, index) => {
    let state = completed[stage.key] ? 'completed' : 'pending';
    if (failed[stage.key]) state = 'failed';
    if (state === 'pending' && incident?.status !== 'resolved' && (runningStage === stage.key || index === nextIndex)) {
      state = 'running';
    }
    return {
      ...stage,
      state,
      detail: stageDetail(stage.key, incident, timeline),
    };
  });
}

export function currentStage(incident, timeline = []) {
  const stages = deriveStages(incident, timeline);
  return stages.find((stage) => stage.state === 'running') ||
    [...stages].reverse().find((stage) => stage.state === 'completed') ||
    stages[0];
}

export function nextAction(incident, timeline = []) {
  if (!incident) return 'Waiting for anomalies across watched services';
  if (incident.status === 'resolved') return incident.post_mortem ? 'Review post-mortem and prevention follow-ups' : 'Post-mortem generation pending';
  if (!incident.hypothesis) return 'Review investigation as the agent builds a hypothesis';
  if (!incident.jira_ticket_id && !incident.slack_message_ts) return 'Coordinate Jira, Slack, and on-call response';
  if (!incident.fix_preview) return 'Generate a fix preview from incident evidence';
  if (!incident.github_pr) return prGateReason(incident) || 'Open a gated GitHub remediation PR';
  if (!hasEvent(incident.timeline || timeline, /rollback_completed|metrics_normalized/)) return 'Review PR or simulate rollback path';
  return 'Resolve incident and generate the post-mortem';
}

export function prGateReason(incident) {
  if (!incident?.fix_preview) return 'Generate a fix preview first';
  if ((incident.confidence || 0) < 40) return 'Confidence must be 40% or higher';
  if (incident.status === 'resolved') return 'Incident already resolved';
  if (incident.github_pr) return '';
  return '';
}

export function engineerBrief(incident, timeline = []) {
  const event = latestEvent(timeline, 'communication_briefs_generated');
  if (event?.metadata?.engineer_brief || incident?.engineer_brief) return event?.metadata?.engineer_brief || incident.engineer_brief;
  const actions = (incident?.recommended_actions || []).join(', ');
  const files = (incident?.fix_preview?.files || []).map((file) => file.path).filter(Boolean).join(', ');
  return [
    incident?.hypothesis || 'Root cause is still being narrowed down.',
    files ? `Likely affected files: ${files}.` : '',
    actions ? `Recommended engineering action: ${actions}.` : 'Recommended engineering action will appear after investigation.',
  ].filter(Boolean).join(' ');
}

export function managerBrief(incident, timeline = []) {
  const event = latestEvent(timeline, 'communication_briefs_generated');
  if (event?.metadata?.manager_brief || incident?.manager_brief) return event?.metadata?.manager_brief || incident.manager_brief;
  const service = incident?.service || 'a monitored service';
  const status = incident?.status === 'resolved' ? 'resolved' : 'being handled';
  const action = incident?.github_pr ? 'A remediation PR is ready for engineering review.' :
    incident?.fix_preview ? 'A fix preview is ready and gated before code changes.' :
      incident?.jira_ticket_id || incident?.slack_message_ts ? 'Slack and Jira response artifacts have been created.' :
        'The agent is investigating and coordinating next steps.';
  return `${service} is ${status}. ${incident?.hypothesis || 'SentinelAI detected an abnormal production signal.'} ${action}`;
}

export function reasoningText(incident) {
  return (incident?.reasoning_chain || []).map((item) => {
    if (typeof item === 'string') return item;
    return `${item.step ? `[${item.step}] ` : ''}${item.detail || ''}`;
  }).filter(Boolean).join(' ');
}

export function artifactBadges(incident, timeline = []) {
  const items = [];
  if (incident?.jira_ticket_id) items.push(['Jira', 'healthy']);
  if (incident?.slack_message_ts) items.push(['Slack', 'healthy']);
  if (incident?.fix_preview) items.push(['Fix preview', 'healthy']);
  if (incident?.github_pr) items.push(['GitHub PR', 'healthy']);
  if (incident?.post_mortem) items.push(['Post-mortem', 'healthy']);
  if (hasEvent(incident?.timeline || timeline, /jira_followups_created/)) items.push(['Prevention tasks', 'healthy']);
  return items;
}

export function durationText(incident) {
  if (!incident?.detected_at) return 'Pending';
  if (incident.duration_minutes !== null && incident.duration_minutes !== undefined) return `${incident.duration_minutes}m`;
  const minutes = Math.max(0, Math.round((Date.now() - new Date(incident.detected_at).getTime()) / 60000));
  return `${minutes}m active`;
}

function hasEvent(timeline = [], pattern) {
  return timeline.some((event) => pattern.test(event.event_type || ''));
}

function failedFor(timeline, key) {
  return timeline.some((event) => (event.event_type || '').includes('failed') && stageFor(event) === key);
}

function stageFor(event) {
  if (!event) return '';
  if (AGENT_STAGE[event.metadata?.agent]) return AGENT_STAGE[event.metadata.agent];
  const type = event.event_type || '';
  if (/detection|signal|anomaly/.test(type)) return 'detection';
  if (/investigation|correlation|root_cause/.test(type)) return 'investigation';
  if (/jira|slack|oncall|response|rollback/.test(type)) return 'response';
  if (/fix_preview|branch|commit/.test(type)) return 'fix';
  if (/github_pr/.test(type)) return 'github_pr';
  if (/post_mortem/.test(type)) return 'post_mortem';
  return '';
}

function stageDetail(stage, incident, timeline) {
  if (stage === 'detection') return incident ? `${incident.service || 'Service'} anomaly captured` : 'Worker watching service signals';
  if (stage === 'investigation') return incident?.hypothesis || latestEvent(timeline, 'correlation_detected')?.description || 'Reasoning pending';
  if (stage === 'response') return incident?.jira_ticket_id || incident?.slack_message_ts ? 'Slack/Jira artifacts created' : 'Response not coordinated yet';
  if (stage === 'fix') return incident?.fix_preview?.title || 'No fix preview generated';
  if (stage === 'github_pr') return incident?.github_pr?.title || 'PR gated until evidence is strong';
  if (stage === 'post_mortem') return incident?.post_mortem ? 'Incident record complete' : 'Generated after resolution';
  return '';
}
