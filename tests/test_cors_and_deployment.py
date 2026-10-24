"""
Tests for CORS configuration, Vercel SPA routing, and deployment configurations.
"""

import os
import json
import re
import pytest
from fastapi.testclient import TestClient
from app.main import app, get_cors_configuration


def test_cors_development_default(monkeypatch):
    """Verifies that development mode provides safe local origins with credentials enabled."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    origins, allow_creds = get_cors_configuration()
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert allow_creds is True
    assert "*" not in origins


def test_cors_custom_origins_parsing(monkeypatch):
    """Verifies safe comma-separated parsing and whitespace stripping."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", " https://cricimpact.vercel.app , https://preview.cricimpact.com,  ")

    origins, allow_creds = get_cors_configuration()
    assert origins == ["https://cricimpact.vercel.app", "https://preview.cricimpact.com"]
    assert allow_creds is True


def test_cors_wildcard_disables_credentials(monkeypatch):
    """Verifies strict security rule: allow_origins=['*'] must NEVER combine with allow_credentials=True."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", " * ")

    origins, allow_creds = get_cors_configuration()
    assert origins == ["*"]
    assert allow_creds is False, "Wildcard origin must never have credentials enabled"


def test_cors_production_fail_closed_when_empty(monkeypatch):
    """Verifies fail-safe behavior: in production, missing CORS_ORIGINS denies all cross-origin access."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    origins, allow_creds = get_cors_configuration()
    assert origins == []
    assert allow_creds is False


def test_cors_live_preflight_headers(monkeypatch):
    """Verifies FastAPI TestClient CORS preflight response headers."""
    client = TestClient(app)

    # Preflight request from allowed local origin
    res = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_vercel_spa_routing_regex():
    """Validates frontend/vercel.json rewrite regex matches client routes but excludes /api."""
    vercel_path = os.path.join("frontend", "vercel.json")
    assert os.path.exists(vercel_path), "frontend/vercel.json must exist"

    with open(vercel_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "rewrites" in config
    assert len(config["rewrites"]) >= 1

    spa_rewrite = next((r for r in config["rewrites"] if r.get("destination") == "/index.html"), None)
    assert spa_rewrite is not None, "A rewrite with destination '/index.html' must exist for SPA routing"
    source_pattern = spa_rewrite["source"]
    destination = spa_rewrite["destination"]

    assert destination == "/index.html"

    # Compile regex pattern
    regex = re.compile(f"^{source_pattern}$")

    # Must match client-side routes
    client_routes = [
        "/",
        "/career",
        "/career/V%20Kohli",
        "/compare",
        "/ground-analysis",
        "/matchups",
        "/dashboard",
        "/matches",
        "/player/V%20Kohli/2024",
        "/match/1426312/player/V%20Kohli",
        "/about",
        "/methodology",
    ]
    for route in client_routes:
        assert regex.match(route) is not None, f"Route '{route}' should be rewritten to index.html"

    # Must NOT match API routes
    api_routes = [
        "/api",
        "/api/",
        "/api/health",
        "/api/dashboard/summary",
        "/api/player/V%20Kohli/2024",
        "/api/matches/1426312",
    ]
    for route in api_routes:
        assert regex.match(route) is None, f"API route '{route}' must NOT be rewritten to index.html"


def test_procfile_format():
    """Validates Procfile syntax and port binding configuration."""
    assert os.path.exists("Procfile"), "Procfile must exist in repository root"

    with open("Procfile", "r", encoding="utf-8") as f:
        content = f.read().strip()

    assert content.startswith("web:"), "Procfile must define web process"
    assert "uvicorn app.main:app" in content
    assert "--host 0.0.0.0" in content
    assert "${PORT:-8000}" in content or "$PORT" in content


def test_frontend_api_url_strategy():
    """
    Validates that frontend API URL strategy in api.js correctly constructs
    /api/... endpoints under development and production environment variables.
    Prevents route mismatch regressions (e.g. 404 from missing /api prefix).
    """
    import subprocess

    api_js_path = os.path.join("frontend", "src", "services", "api.js")
    assert os.path.exists(api_js_path), "frontend/src/services/api.js must exist"

    # Execute Node script importing api.js and asserting outputs
    node_script = """
    import { getApiBaseUrl, buildApiUrl } from './frontend/src/services/api.js';
    import assert from 'node:assert/strict';

    const PROD_RENDER = 'https://cricimpact.onrender.com';
    const PROD_WITH_API = 'https://cricimpact.onrender.com/api';

    // 1. Production base URL resolution
    assert.equal(getApiBaseUrl(PROD_RENDER), 'https://cricimpact.onrender.com/api');
    assert.equal(getApiBaseUrl(PROD_WITH_API), 'https://cricimpact.onrender.com/api');
    assert.equal(getApiBaseUrl(''), '/api');
    assert.equal(getApiBaseUrl(undefined), '/api');

    // 2. Production URL construction for reported 404 routes
    assert.equal(
        buildApiUrl('/competitions', PROD_RENDER),
        'https://cricimpact.onrender.com/api/competitions'
    );
    assert.equal(
        buildApiUrl('/seasons?competition=ipl', PROD_RENDER),
        'https://cricimpact.onrender.com/api/seasons?competition=ipl'
    );
    assert.equal(
        buildApiUrl('/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl', PROD_RENDER),
        'https://cricimpact.onrender.com/api/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl'
    );

    // 3. Local development URL construction (relative /api proxy)
    assert.equal(buildApiUrl('/competitions', undefined), '/api/competitions');
    assert.equal(buildApiUrl('/seasons?competition=ipl', undefined), '/api/seasons?competition=ipl');

    // 4. No duplicate /api when path or env already has /api
    assert.equal(
        buildApiUrl('/api/competitions', PROD_RENDER),
        'https://cricimpact.onrender.com/api/competitions'
    );
    assert.equal(
        buildApiUrl('/competitions', PROD_WITH_API),
        'https://cricimpact.onrender.com/api/competitions'
    );

    console.log('FRONTEND_API_URL_STRATEGY_OK');
    """

    res = subprocess.run(
        ["node", "--input-type=module", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "FRONTEND_API_URL_STRATEGY_OK" in res.stdout
