# api/app.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# FastAPI app with metadata
app = FastAPI(
    title="Energy Data API",
    description="Query processed energy records stored in DynamoDB",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specific domains
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# DynamoDB table reference
TABLE_NAME = os.getenv("DDB_TABLE", "EnergyData")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)  # type: ignore


class EnergyRecord(BaseModel):
    site_id: str
    timestamp: str
    energy_generated_kwh: float
    energy_consumed_kwh: float
    net_energy_kwh: float
    anomaly: bool


@app.get("/records", response_model=list[EnergyRecord])
def get_records(
    site_id: str = Query(..., description="Site identifier"),
    start: str | None = Query(None, description="Start ISO timestamp"),
    end: str | None = Query(None, description="End ISO timestamp"),
):
    """
    Fetch records for a given site, optionally filtered by [start, end] timestamp.
    """
    # Build KeyConditionExpression for site_id and timestamp range if provided
    expr = Key("site_id").eq(site_id)
    if start and end:
        expr = expr & Key("timestamp").between(start, end)
    elif start:
        expr = expr & Key("timestamp").gte(start)
    elif end:
        expr = expr & Key("timestamp").lte(end)

    try:
        resp = TABLE.query(KeyConditionExpression=expr)
    except Exception as e:
        # Log error if desired
        raise HTTPException(status_code=500, detail=f"DynamoDB query error: {e}")

    items = resp.get("Items", [])
    results: list[EnergyRecord] = []
    for it in items:
        # Convert Decimal to float/bool explicitly
        try:
            rec = EnergyRecord(
                site_id=it["site_id"],
                timestamp=it["timestamp"],
                energy_generated_kwh=float(it["energy_generated_kwh"]),
                energy_consumed_kwh=float(it["energy_consumed_kwh"]),
                net_energy_kwh=float(it["net_energy_kwh"]),
                anomaly=bool(it["anomaly"]),
            )
        except Exception as e:
            # If conversion fails, skip or raise
            raise HTTPException(status_code=500, detail=f"Data conversion error: {e}")
        results.append(rec)
    return results


@app.get("/anomalies", response_model=list[EnergyRecord])
def get_anomalies(
    site_id: str = Query(..., description="Site identifier"),
    start: str | None = Query(None, description="Start ISO timestamp"),
    end: str | None = Query(None, description="End ISO timestamp"),
):
    """
    Return only anomaly=True records for a given site, optionally
    filtered by timestamp range.
    """
    # Build KeyConditionExpression as above
    expr = Key("site_id").eq(site_id)
    if start and end:
        expr = expr & Key("timestamp").between(start, end)
    elif start:
        expr = expr & Key("timestamp").gte(start)
    elif end:
        expr = expr & Key("timestamp").lte(end)

    # FilterExpression for anomaly attribute
    filter_expr = Attr("anomaly").eq(True)

    try:
        resp = TABLE.query(KeyConditionExpression=expr, FilterExpression=filter_expr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB query error: {e}")

    items = resp.get("Items", [])
    results: list[EnergyRecord] = []
    for it in items:
        try:
            rec = EnergyRecord(
                site_id=it["site_id"],
                timestamp=it["timestamp"],
                energy_generated_kwh=float(it["energy_generated_kwh"]),
                energy_consumed_kwh=float(it["energy_consumed_kwh"]),
                net_energy_kwh=float(it["net_energy_kwh"]),
                anomaly=bool(it["anomaly"]),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Data conversion error: {e}")
        results.append(rec)
    return results


# If deploying to AWS Lambda + API Gateway, wrap with Mangum
handler = Mangum(app)
