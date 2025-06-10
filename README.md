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
#### Day 2 Verification
- 17 records in DynamoDB  
- 3 anomalies detected (`anomaly = true`)  
- Example anomalous item:

```json
{ "site_id": "site-3", "timestamp": "2025-06-10T20:00:00Z", "energy_generated_kwh": -10, "energy_consumed_kwh": 20, "net_energy_kwh": -30, "anomaly": true }
```

### Day 3 – Alerts & Insights
1. Add Amazon SNS e-mail alert for anomalies  
2. Generate three starter charts (energy vs consumption, anomaly count, net-energy trend)  

#### Day 3 – Visualizations

| Chart | Sample |
|-------|--------|
| Generation vs Consumption (site-1) | ![](visualization/site1_gen_vs_cons.png) |
| Anomalies per Site | ![](visualization/anomaly_counts.png) |
| Net Energy Trend (daily) | ![](visualization/net_energy_trend.png) |

### Day 4 – API Layer
Goals  
1. FastAPI service with `/records` & `/anomalies`  
2. Interactive docs via Swagger UI  
3. Sample queries & README update  

### Day 5 – CI/CD & Polish
1. GitHub Actions workflow (lint + tests + terraform apply)  
2. Build-status badge  
3. Teardown / cost-cleanup checklist  

![ci](https://github.com/NikhilBhoopalam/data-pipeline-project/actions/workflows/deploy.yml/badge.svg)
