import pytest
from fastapi.testclient import TestClient
from api.app import app
import boto3
from moto import mock_aws


@pytest.fixture(autouse=True)
def setup_moto_dynamodb(monkeypatch):
    # Set AWS env vars before boto3 clients are created
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DDB_TABLE", "EnergyData")
    # Dummy credentials so boto3 won’t try real AWS
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")

    with mock_aws():
        # Create the DynamoDB table inside the mock context
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
        yield
    # Exiting the context will tear down the mock


def test_get_records_empty():
    client = TestClient(app)
    resp = client.get("/records?site_id=site-1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_records_with_data():
    from decimal import Decimal

    # Create a boto3 resource inside the mock context
    resource = boto3.resource("dynamodb", region_name="us-east-1")
    table = resource.Table("EnergyData")
    table.put_item(
        Item={
            "site_id": "site-1",
            "timestamp": "2025-06-10T00:00:00Z",
            "energy_generated_kwh": Decimal("50.5"),
            "energy_consumed_kwh": Decimal("20.2"),
            "net_energy_kwh": Decimal("30.3"),
            "anomaly": False,
        }
    )
    client = TestClient(app)
    resp = client.get("/records?site_id=site-1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1
    rec = data[0]
    assert rec["site_id"] == "site-1"
    assert rec["energy_generated_kwh"] == 50.5
    assert rec["anomaly"] is False


def test_get_anomalies():
    from decimal import Decimal

    resource = boto3.resource("dynamodb", region_name="us-east-1")
    table = resource.Table("EnergyData")
    table.put_item(
        Item={
            "site_id": "site-1",
            "timestamp": "2025-06-10T00:01:00Z",
            "energy_generated_kwh": Decimal("-1.0"),
            "energy_consumed_kwh": Decimal("5.0"),
            "net_energy_kwh": Decimal("-6.0"),
            "anomaly": True,
        }
    )
    client = TestClient(app)
    resp = client.get("/anomalies?site_id=site-1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["anomaly"] is True
