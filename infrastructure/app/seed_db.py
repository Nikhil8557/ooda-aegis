"""Builds the demo customer database (fake people, fake tenants)."""
import sqlite3
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "data/customers.db"
rows = [
    ("usr-0001", "tenant-sys", "Global Root Admin", "superadmin@system.example", "superadmin"),
    ("usr-0002", "tenant-finance", "Elena Rostova", "elena@hedgecorp.example", "treasury"),
    ("usr-0003", "tenant-prod-99", "Sarah Connor", "sarah.connor@cyberdyne.example", "engineer"),
    ("usr-0004", "tenant-beta", "Mark Davis", "mdavis@venture.example", "auditor"),
    ("usr-0005", "tenant-prod-99", "Kyle Reese", "kyle.reese@cyberdyne.example", "support"),
]
with sqlite3.connect(path) as conn:
    conn.execute("DROP TABLE IF EXISTS customers")
    conn.execute("CREATE TABLE customers (id TEXT PRIMARY KEY, tenant_id TEXT, full_name TEXT, email TEXT, role TEXT)")
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", rows)
print(f"seeded {len(rows)} customers into {path}")
