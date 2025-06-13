import json
import os
import boto3
from decimal import Decimal
from datetime import datetime


def get_dynamodb_table():
    table_name = os.getenv("DDB_TABLE", "EnergyData")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name=aws_region)
    return dynamodb.Table(table_name)


def get_sns_client():
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("sns", region_name=aws_region)


def get_s3_client():
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("s3", region_name=aws_region)


def lambda_handler(event, context):
    TABLE = get_dynamodb_table()
    SNS = get_sns_client()
    S3 = get_s3_client()
    TOPIC = os.getenv("SNS_TOPIC")

    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = rec["s3"]["object"]["key"]
        body = S3.get_object(Bucket=bucket, Key=key)["Body"].read()
        data = json.loads(body)
        if isinstance(data, dict):
            data = [data]
        for row in data:
            gen = Decimal(str(row["energy_generated_kwh"]))
            con = Decimal(str(row["energy_consumed_kwh"]))
            net = gen - con
            anomaly = (gen < 0) or (con < 0)
            item = {
                "site_id": row["site_id"],
                "timestamp": row["timestamp"],
                "energy_generated_kwh": gen,
                "energy_consumed_kwh": con,
                "net_energy_kwh": net,
                "anomaly": anomaly,
            }
            TABLE.put_item(Item=item)
            print(f"✅ wrote {row['site_id']} {row['timestamp']} anomaly={anomaly}")
            if anomaly and TOPIC:
                timestamp_str = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                subject = f"Energy anomaly {row['site_id']} {timestamp_str}"
                message_body = json.dumps(item, default=str)
                SNS.publish(
                    TopicArn=TOPIC,
                    Subject=subject,
                    Message=message_body,
                )
                print("📣 anomaly alert sent", subject)
    return {"statusCode": 200}
