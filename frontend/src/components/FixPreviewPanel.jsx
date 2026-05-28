import { useState } from 'react';

import { api } from '../api.js';
import { prGateReason } from './incidentStory.js';
import { Button, EmptyState, Panel, SectionHeader, StatusBadge } from './ui.jsx';

export default function FixPreviewPanel({ incident, onRefresh, compact = false }) {
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');

  if (!incident) {
    return (
      <Panel>
        <EmptyState title="No fix preview" copy="Fix analysis appears after an incident has investigation context." />
      </Panel>
    );
  }

  const preview = incident.fix_preview;
  const githubPr = incident.github_pr;
  const disabledReason = githubPr ? '' : prGateReason(incident);
  const canOpenPr = Boolean(preview) && !disabledReason && !githubPr;

  async function run(action, label) {
    setBusy(label);
    setMessage('');
    try {
      const result = await action();
      if (result.status && !['generated', 'existing', 'created'].includes(result.status)) {
        setMessage(result.reason || `GitHub returned status: ${result.status}`);
      } else if (label === 'preview') {
        setMessage('Fix preview is ready for engineering review.');
      } else if (label === 'pr') {
        setMessage('GitHub remediation PR is ready for review.');
      }
      await onRefresh?.();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <Panel className={`fix-preview-panel ${compact ? 'compact' : ''}`}>
      <SectionHeader
        title="Fix preview"
        meta={preview ? preview.summary : 'Generate a reviewable patch from incident evidence before touching GitHub.'}
        action={
          <div className="action-row">
            {preview && <StatusBadge status={`${preview.confidence || incident.confidence || 0}% confidence`} />}
            {githubPr && <StatusBadge status="PR opened" />}
          </div>
        }
      />

      {!preview ? (
        <EmptyState
          title="Generate a fix preview from the incident evidence"
          copy="SentinelAI will use the hypothesis, reasoning chain, and recent GitHub context to produce a reviewable diff."
        />
      ) : (
        <div className="fix-preview-grid">
          <div className="info-box">
            <strong>Target repo</strong>
            <span>{preview.repo || 'Repository not configured'}</span>
          </div>
          <div className="info-box">
            <strong>Source</strong>
            <span>{preview.source || 'generated'}</span>
          </div>
          <div className="info-box">
            <strong>Risk level</strong>
            <span>{preview.risk_level || (preview.confidence >= 80 ? 'low' : 'review required')}</span>
          </div>
          <div className="info-box">
            <strong>Test plan</strong>
            <span>{preview.test_plan || 'Run service tests and validate error-rate recovery before merge.'}</span>
          </div>
          <div className="info-box span-2">
            <strong>Rollback plan</strong>
            <span>{preview.rollback_plan || 'Keep rollback available until metrics normalize and the PR is reviewed.'}</span>
          </div>
          <div className="info-box span-2">
            <strong>{preview.title || 'Proposed fix'}</strong>
            {(preview.files || []).length > 0 ? (
              <div className="file-list">
                {preview.files.map((file) => (
                  <div key={file.path || file.proposed_change}>
                    <code>{file.path || 'unknown file'}</code>
                    <span>{file.proposed_change || file.before_risk || 'Review suggested change.'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span>No file-level evidence returned.</span>
            )}
          </div>
          <pre className="diff-preview span-2">{preview.diff || 'No diff returned.'}</pre>
        </div>
      )}

      {githubPr && (
        <div className="notice success">
          GitHub PR ready:{' '}
          {githubPr.url ? <a href={githubPr.url} target="_blank" rel="noreferrer">{githubPr.title || githubPr.url}</a> : githubPr.title || 'Opened'}
        </div>
      )}
      {message && <div className={message.includes('ready') ? 'notice success' : 'notice'}>{message}</div>}
      {!githubPr && disabledReason && preview && <div className="gate-note">GitHub PR gate: {disabledReason}.</div>}

      <div className="button-row">
        <Button
          loading={busy === 'preview'}
          disabled={Boolean(busy)}
          onClick={() => run(() => api.generateFixPreview(incident.incident_id), 'preview')}
        >
          {preview ? 'Regenerate preview' : 'Generate fix preview'}
        </Button>
        <Button
          variant="primary"
          loading={busy === 'pr'}
          disabled={Boolean(busy) || !canOpenPr}
          title={disabledReason || undefined}
          onClick={() => run(() => api.createGithubPr(incident.incident_id), 'pr')}
        >
          Open GitHub PR
        </Button>
        {githubPr?.url && (
          <Button variant="ghost" onClick={() => window.open(githubPr.url, '_blank', 'noreferrer')}>
            View PR
          </Button>
        )}
      </div>
    </Panel>
  );
}
