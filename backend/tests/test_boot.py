"""Boot + HTTP-path validation under the pinned fastapi/starlette/pydantic.

These tests drive the ASGI app directly via httpx's ASGITransport, deliberately
skipping the full app startup (no lifespan). That exercises the surface the
dependency bumps actually change -- imports, route/schema generation, middleware,
routing, and response serialization -- without depending on the download worker's
event-loop context or external services.
"""
import asyncio

import httpx

from app.main import app


def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)

    async def _run() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(path)

    return asyncio.run(_run())


def test_app_is_fastapi_instance():
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)


def test_openapi_schema_generates():
    schema = app.openapi()
    assert schema.get("openapi", "").startswith("3.")
    assert "/health" in schema["paths"]


def test_health_endpoint_ok():
    r = _get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_security_headers_middleware_runs():
    r = _get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"


def test_unknown_api_route_is_404():
    r = _get("/api/definitely-not-a-route")
    assert r.status_code == 404
