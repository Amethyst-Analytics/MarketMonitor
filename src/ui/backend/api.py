"""FastAPI backend serving data to the Streamlit frontend."""

from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.ui.backend.services import (
    get_auth_status,
    get_latest_prices,
    get_tick_history,
    list_subscribed_instruments,
)

app = FastAPI(title="MarketMonitor API")

__all__ = ["app", "BulkIsinRequest"]


class BulkIsinRequest(BaseModel):
    """Request model for bulk ISIN operations."""

    isins: List[str]


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/auth/status")
def auth_status() -> dict:
    """Return OAuth authentication status."""
    return get_auth_status()


@app.get("/instruments/subscribed")
def subscribed_instruments() -> List[dict]:
    """Return list of subscribed instruments."""
    return list_subscribed_instruments()


@app.post("/isin/bulk")
def bulk_isin(request: BulkIsinRequest) -> dict:
    """Bulk add/remove ISINs from tracking."""
    # Placeholder: implement bulk logic
    return {"added": [], "removed": [], "errors": []}


@app.get("/ticks/latest")
def latest_prices(isins: str) -> dict:
    """Get latest prices for comma-separated ISINs."""
    isin_list = [isin.strip() for isin in isins.split(",") if isin.strip()]
    if not isin_list:
        raise HTTPException(status_code=400, detail="No ISINs provided")
    return get_latest_prices(isin_list)


@app.get("/ticks/history")
def tick_history(isin: str, start: str, end: str) -> List[dict]:
    """Get historical ticks for an ISIN between timestamps."""
    if not isin:
        raise HTTPException(status_code=400, detail="ISIN is required")
    return get_tick_history(isin, start, end)
