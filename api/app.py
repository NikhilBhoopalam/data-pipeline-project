from fastapi import FastAPI, Query
from pydantic import BaseModel
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI(
    title="Energy Data API",
    description="Query processed energy records stored in DynamoDB",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


class EnergyRecord(BaseModel):
    site_id: str
    timestamp: str
    energy_generated_kwh: float
    energy_consumed_kwh: float
    net_energy_kwh: float
    anomaly: bool


def get_dynamodb_table():
    table_name = os.getenv("DDB_TABLE", "EnergyData")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name=aws_region)
    return dynamodb.Table(table_name)


@app.get("/records", response_model=list[EnergyRecord])
def get_records(
    site_id: str = Query(..., description="Site identifier"),
    start: str | None = Query(None, description="Start ISO timestamp"),
    end: str | None = Query(None, description="End ISO timestamp"),
):
    try:
        TABLE = get_dynamodb_table()
    except Exception as e:
        print(f"[ERROR] DynamoDB init error: {e}", flush=True)
        return []

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
            print(f"[ERROR] Data conversion error in /records: {e}", flush=True)
            continue
    return results


@app.get("/anomalies", response_model=list[EnergyRecord])
def get_anomalies(
    site_id: str = Query(..., description="Site identifier"),
    start: str | None = Query(None, description="Start ISO timestamp"),
    end: str | None = Query(None, description="End ISO timestamp"),
):
    try:
        TABLE = get_dynamodb_table()
    except Exception as e:
        print(f"[ERROR] DynamoDB init error: {e}", flush=True)
        return []

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


handler = Mangum(app)
