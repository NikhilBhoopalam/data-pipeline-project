# data-pipeline-project
This is the data pipeline project

# Day 1 Status

## Prerequisites
- AWS account with CLI configured
- Homebrew, AWS CLI, Python 3, Terraform installed

## Terraform Infra
- **S3 bucket:** `$(terraform output -raw data_feed_bucket_bucket)`
- **DynamoDB table:** `EnergyData`
- **Lambda function:** ProcessEnergyData stub

## Test
1. `echo '{"site_id":"site-test","timestamp":"2025-06-06T00:00:00Z"}' > test.json`
2. `aws s3 cp test.json s3://YOUR_BUCKET/test.json`
3. `aws logs tail /aws/lambda/ProcessEnergyData --since 2m`

Lambda logs “pong” event successfully.

---

