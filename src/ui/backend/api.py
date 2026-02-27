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
    """
    Return a simple service health payload.
    
    Returns:
        dict: Mapping with the key "status" set to "ok".
    """
    return {"status": "ok"}


@app.get("/auth/status")
def auth_status() -> dict:
    """
    Get current OAuth authentication status.
    
    Returns:
        dict: Authentication state and related metadata (for example, an `authenticated` flag and any user or token information).
    """
    return get_auth_status()


@app.get("/instruments/subscribed")
def subscribed_instruments() -> List[dict]:
    """
    Retrieve the list of subscribed instruments.
    
    Returns:
        List[dict]: A list of dictionaries representing subscribed instruments.
    """
    return list_subscribed_instruments()


@app.post("/isin/bulk")
def bulk_isin(request: BulkIsinRequest) -> dict:
    """
    Process a bulk request to add or remove ISINs from tracking.
    
    Parameters:
        request (BulkIsinRequest): Request model containing `isins`, a list of ISIN identifier strings to be processed.
    
    Returns:
        result (dict): A dictionary with keys:
            - "added": list of ISINs that were successfully added.
            - "removed": list of ISINs that were successfully removed.
            - "errors": list of error messages for ISINs that failed to process.
    """
    # Placeholder: implement bulk logic
    return {"added": [], "removed": [], "errors": []}


@app.get("/ticks/latest")
def latest_prices(isins: str) -> dict:
    """
    Return latest prices for provided comma-separated ISINs.
    
    Parameters:
        isins (str): Comma-separated ISIN identifiers (e.g. "US1234567890,GB0987654321").
    
    Returns:
        dict: Mapping of ISIN to its latest price data.
    
    Raises:
        HTTPException: If no ISINs are provided (status code 400).
    """
    isin_list = [isin.strip() for isin in isins.split(",") if isin.strip()]
    if not isin_list:
        raise HTTPException(status_code=400, detail="No ISINs provided")
    return get_latest_prices(isin_list)


@app.get("/ticks/history")
def tick_history(isin: str, start: str, end: str) -> List[dict]:
    """
    Retrieve historical tick records for a given ISIN within an inclusive time range.
    
    Parameters:
    	isin (str): The ISIN identifying the instrument.
    	start (str): Start timestamp for the range (timestamp string).
    	end (str): End timestamp for the range (timestamp string).
    
    Returns:
    	List[dict]: A list of tick record dictionaries for the ISIN between start and end.
    """
    if not isin:
        raise HTTPException(status_code=400, detail="ISIN is required")
    return get_tick_history(isin, start, end)
