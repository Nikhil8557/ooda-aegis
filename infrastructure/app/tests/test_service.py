"""The service's own regression tests. OODA-Aegis runs them on every patch."""
from fastapi.testclient import TestClient

from service.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "healthy"


def test_reads_public_document():
    r = client.get("/api/v1/documents/read", params={"file": "quarterly_report_2026.pdf"})
    assert r.status_code == 200 and "Quarterly Report" in r.json()["content"]


def test_missing_document_is_404():
    assert client.get("/api/v1/documents/read", params={"file": "nope.pdf"}).status_code == 404


def test_customer_lookup_returns_one_account():
    r = client.get("/api/v1/auth/customer-lookup",
                   params={"tenant": "tenant-prod-99", "email": "sarah.connor@cyberdyne.example"})
    assert r.status_code == 200 and r.json()["count"] == 1


def test_validator_accepts_and_rejects():
    assert client.get("/api/v1/validator/email-or-domain", params={"input": "a.b@example.com"}).json()["isValid"]
    assert not client.get("/api/v1/validator/email-or-domain", params={"input": "nope"}).json()["isValid"]
