import os
import re
from datetime import timedelta

import requests
from sqlalchemy.orm import Session

from app.models import IntegrationConfig, Service
from app.time_utils import utc_now


class GitHubService:
    def __init__(self, db: Session | None = None, config: dict | None = None):
        self.db = db
        self.config = config or self._db_config() or {}
        self.token = self.config.get("token") or self.config.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN", "")
        self.default_repo = self.config.get("repo") or self.config.get("repository") or os.getenv("GITHUB_REPO", "")

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def recent_commits_for_service(self, service_name: str, since_minutes: int = 60) -> list[dict]:
        repo = self.repo_for_service(service_name)
        return self.get_recent_commits(repo, since_minutes=since_minutes) if repo else []

    def repo_for_service(self, service_name: str) -> str:
        repo = ""
        if self.db:
            service = self.db.query(Service).filter(Service.name == service_name).first()
            repo = service.repo_url if service else ""
        return self._normalize_repo(repo or self.default_repo)

    def get_recent_commits(self, repo: str, since_minutes: int = 60) -> list[dict]:
        repo = self._normalize_repo(repo)
        if not self.token or not repo:
            return []

        since = (utc_now() - timedelta(minutes=since_minutes)).isoformat() + "Z"
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/commits",
                headers=self._headers(),
                params={"since": since, "per_page": 10},
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException:
            return []

        commits = []
        for commit in response.json():
            sha = commit.get("sha", "")
            commits.append(
                {
                    "sha": sha[:7],
                    "message": commit.get("commit", {}).get("message", "").split("\n")[0],
                    "author": commit.get("commit", {}).get("author", {}).get("name"),
                    "timestamp": commit.get("commit", {}).get("author", {}).get("date"),
                    "url": commit.get("html_url"),
                    "files_changed": self._changed_files(repo, sha),
                }
            )
        return commits

    def smoke_test(self) -> dict:
        repo = self._normalize_repo(self.default_repo)
        if not self.token:
            return {"configured": False, "ok": False, "reason": "GitHub token is not configured"}
        if not repo:
            return {"configured": True, "ok": False, "reason": "GitHub repo is not configured"}
        commits = self.get_recent_commits(repo, since_minutes=1440)
        return {"configured": True, "ok": True, "repo": repo, "commit_count": len(commits), "commits": commits[:3]}

    def get_branch_sha(self, repo: str, branch: str) -> str | None:
        repo = self._normalize_repo(repo)
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}",
                headers=self._headers(),
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None
        return response.json().get("object", {}).get("sha")

    def create_branch(self, repo: str, branch: str, base_sha: str) -> dict:
        repo = self._normalize_repo(repo)
        try:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/git/refs",
                headers=self._headers(),
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            if getattr(exc, "response", None) is not None and exc.response.status_code == 422:
                return {"created": False, "exists": True, "branch": branch, "reason": "Branch already exists"}
            return {"created": False, "failed": True, "reason": str(exc)}
        return {"created": True, "branch": branch}

    def get_file(self, repo: str, path: str, ref: str) -> dict:
        repo = self._normalize_repo(repo)
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers=self._headers(),
                params={"ref": ref},
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"ok": False, "reason": str(exc)}
        data = response.json()
        return {
            "ok": True,
            "path": data.get("path", path),
            "sha": data.get("sha"),
            "content": data.get("content", ""),
            "encoding": data.get("encoding"),
        }

    def update_file(self, repo: str, path: str, branch: str, message: str, content_base64: str, sha: str) -> dict:
        repo = self._normalize_repo(repo)
        try:
            response = requests.put(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers=self._headers(),
                json={
                    "message": message,
                    "content": content_base64,
                    "sha": sha,
                    "branch": branch,
                },
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"committed": False, "failed": True, "reason": str(exc)}
        data = response.json()
        return {
            "committed": True,
            "commit_sha": data.get("commit", {}).get("sha"),
            "content_url": data.get("content", {}).get("html_url"),
        }

    def open_pull_request(self, repo: str, title: str, head: str, base: str, body: str) -> dict:
        repo = self._normalize_repo(repo)
        try:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers=self._headers(),
                json={"title": title, "head": head, "base": base, "body": body},
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"opened": False, "failed": True, "reason": str(exc)}
        data = response.json()
        return {
            "opened": True,
            "number": data.get("number"),
            "url": data.get("html_url"),
            "title": data.get("title"),
            "branch": head,
        }

    def _changed_files(self, repo: str, sha: str) -> list[str]:
        if not sha:
            return []
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/commits/{sha}",
                headers=self._headers(),
                timeout=12,
            )
            response.raise_for_status()
        except requests.RequestException:
            return []
        return [item.get("filename") for item in response.json().get("files", []) if item.get("filename")][:5]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    def _db_config(self) -> dict:
        if not self.db:
            return {}
        integration = (
            self.db.query(IntegrationConfig)
            .filter(IntegrationConfig.integration_type == "github", IntegrationConfig.enabled.is_(True))
            .first()
        )
        if not integration:
            return {}
        integration.last_used_at = utc_now()
        return integration.config or {}

    def _normalize_repo(self, repo: str | None) -> str:
        repo = (repo or "").strip().rstrip("/")
        if not repo:
            return ""
        repo = re.sub(r"^https://github\.com/", "", repo)
        repo = re.sub(r"^git@github\.com:", "", repo)
        repo = re.sub(r"\.git$", "", repo)
        return repo if "/" in repo else ""
