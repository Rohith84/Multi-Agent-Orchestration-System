import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db, engine, get_db
from app.models.workflow import Workflow
from app.models.workspace import QualityReport, TestReport
from app.models.metrics import AgentMetric, WorkflowMetric
from sqlalchemy import select


@pytest.mark.asyncio(loop_scope="module")
async def test_phase4_metrics_and_auth():
    """Verify that all metrics are dynamically calculated from DB and protected by JWT auth."""
    await engine.dispose()
    from app.db.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Step 1: Obtain a valid JWT token
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_payload = {
            "username": "admin@enterprise.com",
            "password": "admin123"
        }
        login_res = await ac.post(
            "/api/auth/login",
            data=login_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Test auth protection on analytics and AIOps endpoints
        # Without headers
        unauth_dash = await ac.get("/api/analytics/dashboard")
        assert unauth_dash.status_code == 401
        
        unauth_export = await ac.get("/api/analytics/export")
        assert unauth_export.status_code == 401

        unauth_evals = await ac.get("/api/evaluations")
        assert unauth_evals.status_code == 401

        # With headers - Empty state verification
        auth_dash = await ac.get("/api/analytics/dashboard", headers=headers)
        assert auth_dash.status_code == 200
        dash_data = auth_dash.json()
        
        assert dash_data["total_workflows_executed"] == 0
        assert dash_data["avg_workflow_latency"] is None
        assert dash_data["success_rate_percentage"] is None
        assert dash_data["overall_quality_score"] is None
        assert dash_data["model_stats"] == []
        assert dash_data["tool_stats"] == []
        assert dash_data["rag_stats"] is None
        assert dash_data["token_usage_available"] is False
        assert dash_data["rag_metrics_available"] is False

        # Verify AIOps services are empty (No fake records returned)
        evals_res = await ac.get("/api/evaluations", headers=headers)
        assert evals_res.status_code == 200
        assert evals_res.json()["items"] == []

        drift_res = await ac.get("/api/drift", headers=headers)
        assert drift_res.status_code == 200
        assert drift_res.json()["items"] == []

        opts_res = await ac.get("/api/optimizations", headers=headers)
        assert opts_res.status_code == 200
        assert opts_res.json()["items"] == []

        # Step 3: Insert single successful workflow & verify metrics updates
        # Since we use dependency injection for db session, let's query the db directly
        db_generator = get_db()
        db = await anext(db_generator)

        import uuid
        from datetime import datetime

        wf_id_1 = uuid.uuid4()
        session_id_1 = uuid.uuid4()

        # Insert a completed workflow
        wf1 = Workflow(
            id=wf_id_1,
            session_id=session_id_1,
            title="Workflow 1 Success",
            user_request="Test Request",
            status="completed",
            current_agent="end",
            progress_percentage=100,
            execution_time=12.5,
        )
        db.add(wf1)

        # Insert QualityReport (reviewer output out of 100, we scaled to 9.2 in DB)
        qr1 = QualityReport(
            workflow_id=wf_id_1,
            quality_gate="PASS",
            overall_score=9.2,
        )
        db.add(qr1)

        # Insert AgentMetric for two agents (planner & reviewer)
        am1 = AgentMetric(
            workflow_id=wf_id_1,
            agent_name="planner",
            model="openai/gpt-oss-120b",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=3.2,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            status="success",
            retry_count=0,
            tool_calls=0,
            knowledge_chunks=0,
            score=9.0
        )
        am2 = AgentMetric(
            workflow_id=wf_id_1,
            agent_name="reviewer",
            model="openai/gpt-oss-120b",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=4.5,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            status="success",
            retry_count=0,
            tool_calls=0,
            knowledge_chunks=0,
            score=9.2
        )
        db.add(am1)
        db.add(am2)
        await db.commit()

        # Verify Dashboard KPIs update
        auth_dash = await ac.get("/api/analytics/dashboard", headers=headers)
        assert auth_dash.status_code == 200
        dash_data = auth_dash.json()
        assert dash_data["total_workflows_executed"] == 1
        assert dash_data["avg_workflow_latency"] == 12.5
        assert dash_data["success_rate_percentage"] == 100.0
        assert dash_data["overall_quality_score"] == 9.2
        
        # Verify model stats comparison updates
        model_stats = dash_data["model_stats"]
        assert len(model_stats) == 1
        assert model_stats[0]["model_name"] == "openai/gpt-oss-120b"
        assert model_stats[0]["total_calls"] == 2
        assert model_stats[0]["avg_duration"] == 3.85  # (3.2 + 4.5) / 2
        assert model_stats[0]["avg_score"] == 9.1      # (9.0 + 9.2) / 2
        assert model_stats[0]["success_rate"] == 100.0

        # Step 4: Insert a failed workflow & verify success rate / latency calculations
        wf_id_2 = uuid.uuid4()
        session_id_2 = uuid.uuid4()

        wf2 = Workflow(
            id=wf_id_2,
            session_id=session_id_2,
            title="Workflow 2 Failed",
            user_request="Test Request 2",
            status="failed",
            current_agent="coder",
            progress_percentage=40,
            execution_time=8.0,
            error_message="Coding timeout error"
        )
        db.add(wf2)
        await db.commit()

        # Verify new aggregations
        auth_dash = await ac.get("/api/analytics/dashboard", headers=headers)
        assert auth_dash.status_code == 200
        dash_data = auth_dash.json()
        
        # Success count = 1, Fail count = 1. Total = 2.
        # Success rate = 1 / (1 + 1) * 100 = 50.0%
        assert dash_data["total_workflows_executed"] == 2
        assert dash_data["success_rate_percentage"] == 50.0
        # Avg latency should only aggregate COMPLETED workflows, so it remains 12.5 (from wf1)
        assert dash_data["avg_workflow_latency"] == 12.5
        
        # Verify export formats
        export_json = await ac.get("/api/analytics/export?format=json", headers=headers)
        assert export_json.status_code == 200
        assert "Multi-Agent Workflow Observability Export" in export_json.text

        export_csv = await ac.get("/api/analytics/export?format=csv", headers=headers)
        assert export_csv.status_code == 200
        assert "Metric ID,Workflow ID,Agent Name" in export_csv.text

    await engine.dispose()
