from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import os

TABLE_NAME = os.getenv("DDB_TABLE", "EnergyData")   # same table as Lambda
table = boto3.resource("dynamodb").Table(TABLE_NAME) # type: ignore

app = FastAPI(
    title="Energy Data API",
    description="Query processed energy records stored in DynamoDB",
    version="1.0",
)

class EnergyRecord(BaseModel):
    site_id: str
    timestamp: str
    energy_generated_kwh: float
    energy_consumed_kwh: float
    net_energy_kwh: float
    anomaly: bool

def _convert(item: dict) -> dict:
    """Convert Decimals → float/bool for JSON."""
    for k, v in item.items():
        if isinstance(v, Decimal):
            item[k] = float(v)
    return item

@app.get("/records", response_model=List[EnergyRecord])
def get_records(
    site_id: str = Query(..., description="Site identifier"),
    start: Optional[str] = Query(None, description="Start ISO timestamp"),
    end:   Optional[str] = Query(None, description="End ISO timestamp"),
):
    """
    Fetch records for a given site, optionally filtered by [start, end] timestamp.
    """
    try:
        if start and end:
            resp = table.query(
                KeyConditionExpression=Key("site_id").eq(site_id) &
                                      Key("timestamp").between(start, end)
            )
        else:
            resp = table.query(KeyConditionExpression=Key("site_id").eq(site_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [_convert(it) for it in resp.get("Items", [])]

@app.get("/anomalies", response_model=List[EnergyRecord])
def get_anomalies(site_id: str = Query(..., description="Site identifier")):
    """
    Return only anomaly=True records for a given site.
    """
    try:
        resp = table.query(KeyConditionExpression=Key("site_id").eq(site_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    anomalies = [it for it in resp.get("Items", []) if it.get("anomaly")]
    return [_convert(it) for it in anomalies]
