import boto3
import json
import pytest
from moto import mock_aws
from lambda_function import lambda_handler


@pytest.fixture(autouse=True)
def setup_moto(monkeypatch):
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
        # Create DynamoDB table
        db_client = boto3.client("dynamodb", region_name="us-east-1")
        db_client.create_table(
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
        # Create S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        # Create SNS topic
        sns = boto3.client("sns", region_name="us-east-1")
        resp = sns.create_topic(Name="dummy-topic")
        topic_arn = resp["TopicArn"]
        monkeypatch.setenv("SNS_TOPIC", topic_arn)
        yield
    # Exiting mock_aws context tears down mocks


def test_lambda_handler_puts_item():
    # Put a test object in mocked S3
    s3 = boto3.client("s3", region_name="us-east-1")
    record = {
        "site_id": "site-1",
        "timestamp": "2025-06-10T00:00:00Z",
        "energy_generated_kwh": 10.0,
        "energy_consumed_kwh": 5.0,
    }
    # Write the record JSON to the mocked S3 bucket
    s3.put_object(Bucket="test-bucket", Key="test.json", Body=json.dumps(record))

    # Build S3 event
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test.json"},
                }
            }
        ]
    }
    # Call the lambda handler
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200

    # Verify DynamoDB item was put
    table = boto3.resource("dynamodb", region_name="us-east-1").Table("EnergyData")
    items = table.scan().get("Items", [])
    assert len(items) == 1
    assert items[0]["site_id"] == "site-1"
