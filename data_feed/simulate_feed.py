import argparse
import boto3
import json
import random
import time
import datetime


def make_record(site):
    """Generate a single energy record with possible negative values."""
    return {
        "site_id": site,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "energy_generated_kwh": round(random.uniform(-5, 100), 2),
        "energy_consumed_kwh": round(random.uniform(-5, 100), 2),
    }


def main(bucket, interval):
    s3 = boto3.client("s3")
    sites = [f"site-{i}" for i in range(1, 4)]

    while True:
        rec = make_record(random.choice(sites))
        key = f"data_{rec['site_id']}_{rec['timestamp'].replace(':','-')}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(rec))
        print("⬆️  uploaded", key)
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Simulate energy feed by uploading JSON to S3."
    )
    ap.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket name to upload to"
    )
    ap.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between uploads in seconds (default: 300)",
    )
    args = ap.parse_args()
    main(args.bucket, args.interval)
