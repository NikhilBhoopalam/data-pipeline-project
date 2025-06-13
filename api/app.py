# api/app.py

from fastapi import FastAPI, Query
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
    allow_origins=["*"],  # or restrict to specific domains
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Explicitly get region from environment (Lambda sets AWS_REGION automatically)
aws_region = os.getenv("AWS_REGION", "us-east-1")

# DynamoDB table reference with explicit region
TABLE_NAME = os.getenv("DDB_TABLE", "EnergyData")
try:
    dynamodb = boto3.resource("dynamodb", region_name=aws_region)
    TABLE = dynamodb.Table(TABLE_NAME)  # type: ignore
except Exception as e:
    # If resource creation fails, log it; further calls will raise
    print(f"[INIT ERROR] Failed to initialize DynamoDB resource: {e}", flush=True)
    TABLE = None  # we'll check before usage


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
    Returns an empty list on errors or if no items.
    """
    if TABLE is None:
        # DynamoDB resource wasn't initialized
        print("[ERROR] TABLE is None in get_records", flush=True)
        return []

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
        # Log error to CloudWatch Logs, return empty list
        print(f"[ERROR] DynamoDB query error in /records: {e}", flush=True)
        return []
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
            results.append(rec)
        except Exception as e:
            # Log conversion error and skip this item
            print(f"[ERROR] Data conversion error in /records: {e}", flush=True)
            continue
    return results


@app.get("/anomalies", response_model=list[EnergyRecord])
def get_anomalies(
    site_id: str = Query(..., description="Site identifier"),
    start: str | None = Query(None, description="Start ISO timestamp"),
    end: str | None = Query(None, description="End ISO timestamp"),
):
    """
    Return only anomaly=True records for a given site,
    optionally filtered by timestamp range.
    Returns an empty list on errors or if no items.
    """
    if TABLE is None:
        print("[ERROR] TABLE is None in get_anomalies", flush=True)
        return []

    # Build KeyConditionExpression
    expr = Key("site_id").eq(site_id)
    if start and end:
        expr = expr & Key("timestamp").between(start, end)
    elif start:
        expr = expr & Key("timestamp").gte(start)
    elif end:
        expr = expr & Key("timestamp").lte(end)

    filter_expr = Attr("anomaly").eq(True)
    try:
        resp = TABLE.query(KeyConditionExpression=expr, FilterExpression=filter_expr)
    except Exception as e:
        print(f"[ERROR] DynamoDB query error in /anomalies: {e}", flush=True)
        return []
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
            results.append(rec)
        except Exception as e:
            print(f"[ERROR] Data conversion error in /anomalies: {e}", flush=True)
            continue
    return results


# Wrap with Mangum for AWS Lambda
handler = Mangum(app)
