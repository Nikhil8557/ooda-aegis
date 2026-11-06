"""Customer lookup endpoint (scenario 2: SQL injection, CWE-89)."""
import os
import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = os.getenv("CUSTOMER_DB", "/app/data/customers.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/api/v1/auth/customer-lookup")
def customer_lookup(tenant: str = "", email: str = ""):
    if not tenant or not email:
        raise HTTPException(status_code=400, detail="Both 'tenant' and 'email' are required.")

    query = (
        "SELECT id, tenant_id, full_name, email, role FROM customers "
        f"WHERE tenant_id = '{tenant}' AND email = '{email}'"
    )
    with _connect() as conn:
        rows = [dict(row) for row in conn.execute(query).fetchall()]

    return {"count": len(rows), "accounts": rows}
