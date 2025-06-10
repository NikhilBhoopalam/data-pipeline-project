import json, os, boto3
from decimal import Decimal

TABLE = boto3.resource("dynamodb").Table(os.getenv("DDB_TABLE", "EnergyData"))
S3    = boto3.client("s3")

def lambda_handler(event, context):
    for rec in event["Records"]:
        bucket = rec["s3"]["bucket"]["name"]
        key    = rec["s3"]["object"]["key"]

        body = S3.get_object(Bucket=bucket, Key=key)["Body"].read()
        data = json.loads(body)
        if isinstance(data, dict):
            data = [data]

        for row in data:
            gen = Decimal(str(row["energy_generated_kwh"]))
            con = Decimal(str(row["energy_consumed_kwh"]))
            net = gen - con
            anomaly = (gen < 0) or (con < 0)

            TABLE.put_item(Item={
                "site_id":  row["site_id"],
                "timestamp": row["timestamp"],
                "energy_generated_kwh": gen,
                "energy_consumed_kwh": con,
                "net_energy_kwh": net,
                "anomaly": anomaly,
            })
            print(f"✅ wrote {row['site_id']} {row['timestamp']} anomaly={anomaly}")
    return {"statusCode": 200}
