"""Full app startup (lifespan) validation under the pinned stack.

Unlike ``test_boot.py`` (which drives requests without lifespan via ASGITransport),
this opens the real app through fastapi's ``TestClient`` so the
``@app.on_event("startup")`` lifecycle actually runs: ``init_db()``,
``HUB.bind_loop()``, and the background-loop task scheduling. That catches a
FastAPI/Starlette version change that altered the (deprecated) ``on_event`` startup
path or broke ``init_db()`` on a fresh database.

The download manager's worker spawning is stubbed: it calls module-level
``asyncio.create_task`` (needs a running event loop) and starts background
download/finalize workers that are unrelated to the dependency-bump validation, so
running them here would only add flakiness.
"""
from app.download_manager import DOWNLOAD_MANAGER
from app.main import app


def test_startup_lifecycle_boots_and_serves_health(monkeypatch):
    monkeypatch.setattr(DOWNLOAD_MANAGER, "start", lambda: None)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        # The generated OpenAPI schema is also served over the full HTTP stack.
        o = client.get("/openapi.json")
        assert o.status_code == 200
        assert o.json().get("openapi", "").startswith("3.")
