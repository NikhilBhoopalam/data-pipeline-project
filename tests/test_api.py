# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from api.app import app
import boto3
from moto import mock_dynamodb2


@pytest.fixture(autouse=True)
def setup_moto_dynamodb(monkeypatch):
    # Start moto mock
    with mock_dynamodb2():
        # Create a fake table
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="EnergyData",
            KeySchema=[
                {"AttributeName": "site_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "site_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        # Ensure environment variable for table name
        monkeypatch.setenv("DDB_TABLE", "EnergyData")
        yield
        # moto will clean up on exit


def test_get_records_empty():
    client = TestClient(app)
    resp = client.get("/records?site_id=test-site")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_records_with_data():
    # Insert an item into the fake table
    resource = boto3.resource("dynamodb", region_name="us-east-1")
    table = resource.Table("EnergyData")
    table.put_item(
        Item={
            "site_id": "test-site",
            "timestamp": "2025-06-10T00:00:00Z",
            "energy_generated_kwh": 50.5,
            "energy_consumed_kwh": 20.2,
            "net_energy_kwh": 30.3,
            "anomaly": False,
        }
    )
    client = TestClient(app)
    resp = client.get("/records?site_id=test-site")
    data = resp.json()
    assert resp.status_code == 200
    assert isinstance(data, list) and len(data) == 1
    rec = data[0]
    assert rec["site_id"] == "test-site"
    assert rec["energy_generated_kwh"] == 50.5
    assert rec["anomaly"] is False


def test_get_anomalies():
    resource = boto3.resource("dynamodb", region_name="us-east-1")
    table = resource.Table("EnergyData")
    table.put_item(
        Item={
            "site_id": "test-site",
            "timestamp": "2025-06-10T00:01:00Z",
            "energy_generated_kwh": -1.0,
            "energy_consumed_kwh": 5.0,
            "net_energy_kwh": -6.0,
            "anomaly": True,
        }
    )
    client = TestClient(app)
    resp = client.get("/anomalies?site_id=test-site")
    data = resp.json()
    assert resp.status_code == 200
    assert len(data) == 1
    assert data[0]["anomaly"] is True
