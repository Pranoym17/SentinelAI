from datetime import timedelta

from sqlalchemy import inspect

from app.database import Base, SessionLocal, engine
from app.models import IntegrationConfig, OnCallSchedule, RunbookLibrary, SLARecord, Service
from app.time_utils import utc_now


def test_phase_a_tables_are_registered_and_created():
    expected_tables = {
        "services",
        "sla_records",
        "on_call_schedule",
        "runbook_library",
        "integration_configs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables.keys()))

    table_names = inspect(engine).get_table_names()
    assert expected_tables.issubset(set(table_names))


def test_service_model_insert_defaults():
    db = SessionLocal()
    try:
        service = Service(name="payments", display_name="Payments API", team="payments-team")
        db.add(service)
        db.commit()
        db.refresh(service)

        assert service.id
        assert service.dependencies == []
        assert service.sla_target == 99.9
        assert service.created_at is not None
    finally:
        db.close()


def test_sla_record_model_insert_defaults():
    db = SessionLocal()
    try:
        record = SLARecord(service="payments", month="2026-05")
        db.add(record)
        db.commit()
        db.refresh(record)

        assert record.target_uptime == 99.9
        assert record.total_downtime_minutes == 0
        assert record.incident_count == 0
        assert record.sla_breached is False
    finally:
        db.close()


def test_oncall_runbook_and_integration_models_insert():
    db = SessionLocal()
    now = utc_now()
    try:
        oncall = OnCallSchedule(
            engineer_name="Sarah",
            engineer_email="sarah@example.com",
            slack_handle="@sarah",
            team="payments-team",
            start_time=now,
            end_time=now + timedelta(hours=8),
        )
        runbook = RunbookLibrary(
            service="payments",
            signal_type="error_spike",
            title="Payments rollback",
            steps=["Check deploy", "Rollback", "Verify metrics"],
        )
        integration = IntegrationConfig(
            integration_type="github",
            enabled=True,
            config={"repo": "example/payments-api"},
            connected_at=now,
        )
        db.add_all([oncall, runbook, integration])
        db.commit()

        assert db.query(OnCallSchedule).first().is_active is True
        assert db.query(RunbookLibrary).first().times_used == 0
        assert db.query(IntegrationConfig).first().config["repo"] == "example/payments-api"
    finally:
        db.close()
