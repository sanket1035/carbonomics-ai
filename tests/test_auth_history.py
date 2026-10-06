"""Tests for the login check, the history storage calls and the run endpoints.
Supabase is replaced by a locally generated signing key and an in-memory fake of its REST API."""

import time
import uuid

import httpx
import jwt
import pandas as pd
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from api import auth, history
from api.main import app

URL = "https://proj.supabase.co"
ANON = "anon-key-for-tests"
client = TestClient(app)
USER_ID = str(uuid.uuid4())


def make_key():
    private = ec.generate_private_key(ec.SECP256R1())
    return private, private.public_key()


PRIVATE, PUBLIC = make_key()
OTHER_PRIVATE, _ = make_key()


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJwks:
    def get_signing_key_from_jwt(self, token):
        return FakeSigningKey(PUBLIC)


def token(sub=USER_ID, key=PRIVATE, alg="ES256", **over):
    now = int(time.time())
    claims = {"sub": sub, "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": now + 600, "iat": now,
              "role": "authenticated", "email": "principal@example.com", **over}
    return jwt.encode(claims, key, algorithm=alg)


def bearer(**kw):
    return {"Authorization": f"Bearer {token(**kw)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON)
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setattr(auth, "_jwks_client", lambda url: FakeJwks())


class FakeSupabase:
    """Just enough of PostgREST for /rest/v1/runs: records every request, stores rows per bearer token."""

    def __init__(self):
        self.requests = []
        self.rows = []
        self.fail = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            return httpx.Response(500, json={"message": "boom"})
        who = request.headers["authorization"]
        mine = [r for r in self.rows if r["_owner"] == who]
        if request.method == "POST":
            import json
            row = {**json.loads(request.content), "id": str(uuid.uuid4()), "_owner": who, "created_at": "2026-10-06T00:00:00Z"}
            self.rows.append(row)
            return httpx.Response(201, json=[{k: v for k, v in row.items() if k != "_owner"}])
        if request.method == "GET":
            rid = request.url.params.get("id")
            if rid:
                mine = [r for r in mine if rid == f"eq.{r['id']}"]
            return httpx.Response(200, json=[{k: v for k, v in r.items() if k != "_owner"} for r in mine])
        if request.method == "DELETE":
            rid = request.url.params["id"]
            gone = [r for r in mine if rid == f"eq.{r['id']}"]
            self.rows = [r for r in self.rows if r not in gone]
            return httpx.Response(200, json=[{"id": r["id"]} for r in gone])
        return httpx.Response(405)


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(history, "_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handler)))
    return fake


def weekly_csv(n=52):
    import numpy as np
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"week_start": pd.date_range("2025-01-01", periods=n, freq="7D"),
                       "electricity_kwh": 20000 + rng.normal(0, 300, n), "diesel_litres": rng.uniform(0, 40, n)})
    return df.to_csv(index=False).encode()


def analyze(headers, **data):
    return client.post("/api/analyze", headers=headers, files={"file": ("college.csv", weekly_csv(), "text/csv")}, data=data)


# ── login check ───────────────────────────────────────────────────────────────
def test_health_needs_no_login():
    assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("path,method", [("/api/analyze", "post"), ("/api/simulate", "post"), ("/api/optimize", "post"),
                                         ("/api/runs", "get"), (f"/api/runs/{uuid.uuid4()}", "get"),
                                         (f"/api/runs/{uuid.uuid4()}", "delete")])
def test_every_data_route_needs_a_login(path, method):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("headers", [
    {"Authorization": "Bearer not-a-token"},
    {"Authorization": "Basic abc"},
    bearer(exp=int(time.time()) - 10),                       # expired
    bearer(aud="anon"),                                       # wrong audience
    bearer(iss="https://evil.example/auth/v1"),               # wrong issuer
    bearer(key=OTHER_PRIVATE),                                # signed with someone else's key
])
def test_bad_tokens_are_rejected(headers):
    r = client.get("/api/runs", headers=headers)
    assert r.status_code == 401


def test_token_signed_with_the_public_key_as_hmac_secret_is_rejected():
    pem = PUBLIC.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    # PyJWT itself refuses to build this token, so assemble it by hand the way an attacker would
    import base64, hashlib, hmac, json

    def b64(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=")
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"sub": USER_ID, "aud": "authenticated", "iss": f"{URL}/auth/v1",
                           "exp": int(time.time()) + 600}).encode())
    sig = b64(hmac.new(pem, head + b"." + body, hashlib.sha256).digest())
    forged = (head + b"." + body + b"." + sig).decode()
    assert client.get("/api/runs", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_token_without_expiry_is_rejected():
    claims = {"sub": USER_ID, "aud": "authenticated", "iss": f"{URL}/auth/v1"}
    t = jwt.encode(claims, PRIVATE, algorithm="ES256")
    assert client.get("/api/runs", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_server_without_login_config_refuses_instead_of_opening_up(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL")
    assert client.get("/api/runs", headers=bearer()).status_code == 503


def test_keys_unreachable_is_a_503_not_a_pass(monkeypatch):
    class Down:
        def get_signing_key_from_jwt(self, t):
            raise jwt.PyJWKClientConnectionError("down")
    monkeypatch.setattr(auth, "_jwks_client", lambda url: Down())
    assert client.get("/api/runs", headers=bearer()).status_code == 503


def test_dev_switch_skips_login_and_history(monkeypatch, db):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    r = analyze({})
    assert r.status_code == 200 and r.json()["run"]["saved"] is False
    assert db.requests == []


# ── saving and reading history ────────────────────────────────────────────────
def test_analysis_is_saved_with_the_users_own_token(db):
    h = bearer()
    r = analyze(h, title="FY25 baseline")
    assert r.status_code == 200
    run = r.json()["run"]
    assert run["saved"] is True and run["id"]
    req = db.requests[0]
    assert str(req.url) == f"{URL}/rest/v1/runs" and req.method == "POST"
    assert req.headers["authorization"] == h["Authorization"] and req.headers["apikey"] == ANON
    import json
    body = json.loads(req.content)
    assert "user_id" not in body                      # the database fills it from the token
    assert body["kind"] == "analysis" and body["title"] == "FY25 baseline"
    assert body["input"]["file_name"] == "college.csv" and body["input"]["rows"] == 52
    assert body["summary"]["total_tco2e"] > 0
    assert "periods" in body["result"]["accounting"]


def test_a_failed_save_does_not_hide_the_analysis(db):
    db.fail = True
    r = analyze(bearer())
    assert r.status_code == 200
    assert r.json()["run"]["saved"] is False and "refused" in r.json()["run"]["error"]
    assert r.json()["accounting"]["totals"]["total_tco2e"] > 0


def test_simulation_is_saved_only_on_request_and_links_to_its_analysis(db):
    h = bearer()
    first = analyze(h).json()
    periods = [{k: v for k, v in p.items() if k in ("period_start", "electricity_kwh", "diesel_litres")}
               for p in first["accounting"]["periods"]]
    body = {"periods": periods, "electricity_change_pct": -10}
    n = len(db.requests)
    r = client.post("/api/simulate", headers=h, json=body)
    assert r.status_code == 200 and "run" not in r.json() and len(db.requests) == n   # slider moves are not saved
    r = client.post("/api/simulate", headers=h, json={**body, "save": True, "title": "10% less",
                                                      "parent_run_id": first["run"]["id"]})
    assert r.json()["run"]["saved"] is True
    import json
    saved = json.loads(db.requests[-1].content)
    assert saved["kind"] == "simulation" and saved["parent_run_id"] == first["run"]["id"]
    assert saved["input"]["electricity_change_pct"] == -10


def test_users_only_see_and_delete_their_own_runs(db):
    mine, theirs = bearer(), bearer(sub=str(uuid.uuid4()))
    run_id = analyze(mine).json()["run"]["id"]
    assert [x["id"] for x in client.get("/api/runs", headers=mine).json()] == [run_id]
    assert client.get("/api/runs", headers=theirs).json() == []
    assert client.get(f"/api/runs/{run_id}", headers=theirs).status_code == 404
    assert client.delete(f"/api/runs/{run_id}", headers=theirs).status_code == 404
    assert client.get(f"/api/runs/{run_id}", headers=mine).json()["id"] == run_id
    assert client.delete(f"/api/runs/{run_id}", headers=mine).json() == {"deleted": True}
    assert client.get("/api/runs", headers=mine).json() == []


def test_list_asks_only_for_the_small_columns_newest_first(db):
    client.get("/api/runs?limit=999", headers=bearer())
    q = db.requests[-1].url.params
    assert q["select"] == history.LIST_COLUMNS and "result" not in q["select"]
    assert q["order"] == "created_at.desc" and q["limit"] == "200"      # capped


def test_run_id_must_be_a_uuid(db):
    assert client.get("/api/runs/not-a-uuid", headers=bearer()).status_code == 422
    assert db.requests == []                                          # nothing reached the database


def test_oversized_results_are_trimmed_before_saving():
    big = {"accounting": {"totals": {"total_tco2e": 1}, "periods": [{"x": "y" * 100}] * 30000}, "input": {}}
    small = history.shrink(big)
    assert small["truncated"] is True and "periods" not in small["accounting"]
    assert small["accounting"]["totals"]["total_tco2e"] == 1
    assert history.shrink({"a": 1}) == {"a": 1}


def test_optimization_plan_is_saved_only_on_request_as_its_own_kind(db):
    h = bearer()
    body = {"periods": [{"period_start": f"2025-{m:02d}-01", "electricity_kwh": 90000.0} for m in range(1, 13)],
            "granularity": "monthly", "budget_inr": 4_000_000,
            "measures": [{"label": "Solar", "acts_on": "electricity", "saving_type": "fixed_kwh_per_year",
                          "saving_value": 140000, "capex_inr": 3_300_000, "max_units": 3}]}
    n = len(db.requests)
    r = client.post("/api/optimize", headers=h, json=body)
    assert r.status_code == 200 and "run" not in r.json() and len(db.requests) == n
    r = client.post("/api/optimize", headers=h, json={**body, "save": True, "title": "33 lakh solar"})
    assert r.json()["run"]["saved"] is True
    import json
    saved = json.loads(db.requests[-1].content)
    assert saved["kind"] == "optimization" and saved["title"] == "33 lakh solar"
    assert saved["input"]["budget_inr"] == 4_000_000 and saved["summary"]["tco2e_saved"] > 0


def test_report_is_a_pdf_for_logged_in_users_only_and_includes_the_plan(db):
    import io
    pypdf = pytest.importorskip("pypdf")
    periods = [{"period_start": f"2025-{m:02d}-01", "electricity_kwh": 90000.0, "diesel_litres": 100.0} for m in range(1, 13)]
    body = {"periods": periods, "granularity": "monthly", "file_name": "college.xlsx", "prepared_for": "Dr. A. B. Name, Principal",
            "budget_inr": 4_000_000,
            "measures": [{"label": "Solar", "acts_on": "electricity", "saving_type": "fixed_kwh_per_year",
                          "saving_value": 140000, "capex_inr": 3_300_000, "max_units": 3}]}
    assert client.post("/api/report", json=body).status_code == 401
    r = client.post("/api/report", headers=bearer(), json=body)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    pages = pypdf.PdfReader(io.BytesIO(r.content)).pages
    text = "\n".join(p.extract_text() for p in pages)
    assert len(pages) == 13 and "Recommended steps" in text and "Dr. A. B. Name" in text and "college.xlsx" in text
    r2 = client.post("/api/report", headers=bearer(), json={k: v for k, v in body.items() if k not in ("budget_inr", "measures")})
    assert len(pypdf.PdfReader(io.BytesIO(r2.content)).pages) == 11
    assert db.requests == []                                       # nothing is stored for a report


def test_allowed_origin_with_trailing_slash_still_matches(monkeypatch):
    import importlib

    import api.main as main_mod

    monkeypatch.setenv("ALLOWED_ORIGINS", "https://site.example/")
    try:
        mod = importlib.reload(main_mod)
        r = TestClient(mod.app).get("/api/health", headers={"Origin": "https://site.example"})
        assert r.headers.get("access-control-allow-origin") == "https://site.example"
    finally:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        importlib.reload(main_mod)
