import base64
import os
import re

from sqlalchemy.orm import Session

from app.models import Incident
from app.services.commander_service import CommanderService
from app.services.fix_preview_service import FixPreviewService
from app.services.github_service import GitHubService
from app.services.timeline_service import TimelineService


class GitHubPRService:
    def __init__(self, db: Session, github: GitHubService | None = None):
        self.db = db
        self.github = github or GitHubService(db)
        self.timeline = TimelineService(db)
        self.commander = CommanderService(db)
        self.enabled = os.getenv("GITHUB_PR_ENABLED", "false").lower() == "true"
        self.base_branch = os.getenv("GITHUB_PR_BASE_BRANCH", "main")
        self.branch_prefix = os.getenv("GITHUB_PR_BRANCH_PREFIX", "sentinel")

    def create_pr(self, incident: Incident) -> dict:
        if incident.github_pr:
            return {"status": "existing", "github_pr": incident.github_pr}
        if not self.enabled:
            return {"status": "disabled", "reason": "GITHUB_PR_ENABLED is not true"}
        if not self.github.configured:
            return {"status": "skipped", "reason": "GitHub token is not configured"}
        if incident.confidence is not None and incident.confidence < 80:
            return {"status": "blocked", "reason": "GitHub PR requires high-confidence incident"}

        if not incident.fix_preview:
            preview_result = FixPreviewService(self.db).generate(incident)
            incident.fix_preview = preview_result["fix_preview"]

        preview = incident.fix_preview or {}
        repo = preview.get("repo") or self.github.repo_for_service(incident.service)
        target_path = self._target_path(preview)
        if not repo or not target_path:
            return {"status": "skipped", "reason": "No GitHub repo or target file available"}

        self.commander.started(
            incident.id,
            "GitHubFixAgent",
            f"Opening GitHub PR for {target_path}",
            {"repo": repo},
        )

        branch = self._branch_name(incident)
        base_sha = self.github.get_branch_sha(repo, self.base_branch)
        if not base_sha:
            self.commander.failed(incident.id, "GitHubFixAgent", "Could not resolve base branch", {"repo": repo})
            return {"status": "failed", "reason": f"Could not resolve base branch {self.base_branch}"}

        branch_result = self.github.create_branch(repo, branch, base_sha)
        if branch_result.get("failed"):
            self.timeline.append(incident.id, "github_branch_failed", branch_result["reason"], branch_result)
            self.commander.failed(incident.id, "GitHubFixAgent", "Could not create GitHub branch", branch_result)
            return {"status": "failed", "reason": branch_result["reason"]}
        self.timeline.append(
            incident.id,
            "github_branch_created",
            f"GitHub branch ready: {branch}",
            {"repo": repo, **branch_result},
        )

        file_result = self.github.get_file(repo, target_path, branch)
        if not file_result.get("ok"):
            self.timeline.append(incident.id, "github_file_failed", file_result.get("reason", "Could not read file"), file_result)
            return {"status": "failed", "reason": file_result.get("reason", "Could not read file")}

        new_content = self._patched_content(file_result, preview)
        commit_result = self.github.update_file(
            repo=repo,
            path=target_path,
            branch=branch,
            message=preview.get("title") or f"SentinelAI fix for incident {incident.id}",
            content_base64=base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
            sha=file_result["sha"],
        )
        if not commit_result.get("committed"):
            self.timeline.append(incident.id, "github_commit_failed", commit_result.get("reason", "Commit failed"), commit_result)
            self.commander.failed(incident.id, "GitHubFixAgent", "Could not commit GitHub fix", commit_result)
            return {"status": "failed", "reason": commit_result.get("reason", "Commit failed")}

        self.timeline.append(
            incident.id,
            "github_commit_created",
            f"GitHub fix commit created on {branch}",
            {"repo": repo, "branch": branch, **commit_result},
        )

        pr_result = self.github.open_pull_request(
            repo=repo,
            title=preview.get("title") or f"SentinelAI fix for incident {incident.id}",
            head=branch,
            base=self.base_branch,
            body=self._pr_body(incident, preview, commit_result),
        )
        if not pr_result.get("opened"):
            self.timeline.append(incident.id, "github_pr_failed", pr_result.get("reason", "PR creation failed"), pr_result)
            self.commander.failed(incident.id, "GitHubFixAgent", "Could not open GitHub PR", pr_result)
            return {"status": "failed", "reason": pr_result.get("reason", "PR creation failed")}

        incident.github_pr = {
            "repo": repo,
            "branch": branch,
            "base_branch": self.base_branch,
            "number": pr_result.get("number"),
            "url": pr_result.get("url"),
            "title": pr_result.get("title"),
            "commit_sha": commit_result.get("commit_sha"),
        }
        self.timeline.append(
            incident.id,
            "github_pr_created",
            f"GitHub PR opened: {pr_result.get('url')}",
            incident.github_pr,
        )
        self.commander.completed(
            incident.id,
            "GitHubFixAgent",
            "GitHub PR opened",
            incident.github_pr,
        )
        self.db.commit()
        self.db.refresh(incident)
        return {"status": "created", "github_pr": incident.github_pr}

    def _target_path(self, preview: dict) -> str:
        files = preview.get("files") or []
        if files and files[0].get("path"):
            return files[0]["path"]
        diff = preview.get("diff") or ""
        match = re.search(r"^\+\+\+ b/(.+)$", diff, flags=re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _branch_name(self, incident: Incident) -> str:
        service = re.sub(r"[^a-zA-Z0-9-]+", "-", incident.service).strip("-").lower()
        return f"{self.branch_prefix}/fix-incident-{incident.id}-{service}"

    def _patched_content(self, file_result: dict, preview: dict) -> str:
        raw = file_result.get("content") or ""
        try:
            current = base64.b64decode(raw).decode("utf-8")
        except Exception:
            current = ""
        marker = (
            "\n\n"
            "# SentinelAI suggested fix preview\n"
            "# Review before merging. Generated from incident context.\n"
        )
        diff_comment = "\n".join(f"# {line}" for line in (preview.get("diff") or "").splitlines()[:80])
        return f"{current.rstrip()}{marker}{diff_comment}\n"

    def _pr_body(self, incident: Incident, preview: dict, commit_result: dict) -> str:
        reasoning = "\n".join(
            f"- [{step.get('step', 'STEP')}] {step.get('detail', '')}"
            for step in (incident.reasoning_chain or [])
        )
        return (
            f"## SentinelAI incident fix\n\n"
            f"Incident: #{incident.id}\n\n"
            f"Service: `{incident.service}`\n\n"
            f"Severity: `{incident.severity}`\n\n"
            f"Confidence: `{incident.confidence}%`\n\n"
            f"Jira: {incident.jira_ticket_url or 'not available'}\n\n"
            f"## Hypothesis\n{incident.hypothesis or 'No hypothesis captured'}\n\n"
            f"## Fix summary\n{preview.get('summary') or 'No summary provided'}\n\n"
            f"## Reasoning\n{reasoning or 'No reasoning chain captured'}\n\n"
            f"## Commit\n{commit_result.get('commit_sha') or 'pending'}\n\n"
            "This PR was opened by SentinelAI for review. Do not merge without human validation.\n"
        )
