"""Email validation endpoint (scenario 3: ReDoS, CWE-1333)."""
import re
import time

from fastapi import APIRouter, HTTPException

router = APIRouter()

EMAIL_PATTERN = re.compile(r"^([a-zA-Z0-9]+\.?)+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")


@router.get("/api/v1/validator/email-or-domain")
def validate_email(input: str = ""):
    if not input:
        raise HTTPException(status_code=400, detail="Missing required query parameter: 'input'")

    started = time.perf_counter()
    is_valid = bool(EMAIL_PATTERN.match(input))
    elapsed_ms = (time.perf_counter() - started) * 1000

    return {"input": input, "isValid": is_valid, "elapsedMs": round(elapsed_ms, 2)}
