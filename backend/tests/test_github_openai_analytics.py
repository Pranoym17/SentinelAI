import json
from datetime import timedelta
from unittest.mock import Mock, patch

from app.database import SessionLocal
from app.models import Incident, Service, SLARecord
from app.services.github_service import GitHubService
from app.services.openai_service import OpenAIService
from app.time_utils import utc_now


def test_github_service_reads_recent_commits_for_service_repo(client):
    client.post(
        "/api/services",
        json={"name": "payments", "repo_url": "https://github.com/example/payments-api"},
    )
    client.post(
        "/api/integrations",
        json={"type": "github", "enabled": True, "config": {"token": "gh-test"}},
    )

    commits_response = Mock()
    commits_response.json.return_value = [
        {
            "sha": "abcdef123456",
            "html_url": "https://github.com/example/payments-api/commit/abcdef1",
            "commit": {
                "message": "Tune payment timeout\n\nbody",
                "author": {"name": "Priya", "date": "2026-05-27T12:00:00Z"},
            },
        }
    ]
    commits_response.raise_for_status = Mock()
    detail_response = Mock()
    detail_response.json.return_value = {"files": [{"filename": "payments/client.py"}]}
    detail_response.raise_for_status = Mock()

    with patch("app.services.github_service.requests.get", side_effect=[commits_response, detail_response]) as get:
        with SessionLocal() as db:
            commits = GitHubService(db).recent_commits_for_service("payments")

    assert commits == [
        {
            "sha": "abcdef1",
            "message": "Tune payment timeout",
            "author": "Priya",
            "timestamp": "2026-05-27T12:00:00Z",
            "url": "https://github.com/example/payments-api/commit/abcdef1",
            "files_changed": ["payments/client.py"],
        }
    ]
    assert get.call_args_list[0].args[0] == "https://api.github.com/repos/example/payments-api/commits"


def test_github_test_endpoint_uses_db_config(client):
    client.post(
        "/api/integrations",
        json={"type": "github", "enabled": True, "config": {"token": "gh-test", "repo": "example/payments-api"}},
    )
    response = Mock()
    response.json.return_value = []
    response.raise_for_status = Mock()

    with patch("app.services.github_service.requests.get", return_value=response):
        result = client.post("/api/integrations/github/test").json()

    assert result["configured"] is True
    assert result["ok"] is True
    assert result["repo"] == "example/payments-api"


def test_investigation_context_includes_github_commit_and_stores_recommended_actions(client):
    client.post(
        "/api/config",
        json={
            "services": ["payments"],
            "signals": ["error_spike"],
            "actions": [],
            "thresholds": {"error_rate": 5},
            "slack_channel": "#incidents",
            "jira_project_key": "INC",
        },
    )
    client.post(
        "/api/services",
        json={"name": "payments", "repo_url": "example/payments-api"},
    )
    client.post(
        "/api/integrations",
        json={"type": "github", "enabled": True, "config": {"token": "gh-test"}},
    )
    commits_response = Mock()
    commits_response.json.return_value = [
        {
            "sha": "fedcba987654",
            "html_url": "https://github.com/example/payments-api/commit/fedcba9",
            "commit": {
                "message": "Change SDK retry policy",
                "author": {"name": "Dev", "date": "2026-05-27T12:00:00Z"},
            },
        }
    ]
    commits_response.raise_for_status = Mock()
    detail_response = Mock()
    detail_response.json.return_value = {"files": [{"filename": "payments/sdk.py"}]}
    detail_response.raise_for_status = Mock()

    with patch("app.services.github_service.requests.get", side_effect=[commits_response, detail_response]):
        incident = client.post(
            "/api/signal",
            json={"service": "payments", "type": "error_spike", "value": 18.0, "baseline": 0.2},
        ).json()

    steps = [step["step"] for step in incident["reasoning_chain"]]
    assert "CHECKING COMMITS" in steps
    assert "fedcba9" in json.dumps(incident["reasoning_chain"])
    assert incident["recommended_actions"]


def test_openai_investigation_retries_and_stores_raw_response():
    valid = {
        "reasoning_chain": [{"step": "SIGNAL DETECTED", "detail": "Spike", "confidence": 50}],
        "hypothesis": "Deploy regression",
        "confidence": 82,
        "severity": "SEV-1",
        "affected_teams": ["payments"],
        "recommended_actions": ["Rollback"],
    }
    bad_choice = Mock()
    bad_choice.message.content = "{}"
    good_choice = Mock()
    good_choice.message.content = json.dumps(valid)
    service = OpenAIService()
    service.client = Mock()
    service.client.chat.completions.create.side_effect = [
        Mock(choices=[bad_choice]),
        Mock(choices=[good_choice]),
    ]

    result = service.investigate({"service": "payments"}, {"recent_commits": []})

    assert result.hypothesis == "Deploy regression"
    assert result.raw_model_response == json.dumps(valid)
    assert service.client.chat.completions.create.call_count == 2


def test_analytics_reports_severity_mttr_and_sla_history(client):
    with SessionLocal() as db:
        db.add(
            Incident(
                service="payments",
                signal_type="error_spike",
                signal_value=18.0,
                severity="SEV-1",
                status="resolved",
                hypothesis="Deploy regression",
                confidence=90,
                duration_minutes=12,
                detected_at=utc_now() - timedelta(minutes=20),
                resolved_at=utc_now(),
            )
        )
        db.add(
            Incident(
                service="auth",
                signal_type="latency_spike",
                signal_value=2500,
                severity="SEV-2",
                status="resolved",
                hypothesis=None,
                confidence=60,
                duration_minutes=6,
                detected_at=utc_now() - timedelta(minutes=20),
                resolved_at=utc_now(),
            )
        )
        db.add(
            SLARecord(
                service="payments",
                month=utc_now().strftime("%Y-%m"),
                target_uptime=99.9,
                actual_uptime=99.8,
                total_downtime_minutes=80,
                incident_count=2,
                sla_breached=True,
            )
        )
        db.commit()

    analytics = client.get("/api/analytics").json()

    assert analytics["by_severity"] == {"SEV-1": 1, "SEV-2": 1}
    assert analytics["mttr_by_service"] == {"payments": 12.0, "auth": 6.0}
    assert analytics["sla_breach_history"][0]["sla_breached"] is True
    assert analytics["agent_accuracy"] == 50.0
