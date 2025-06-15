# ⚡ Renewable-Energy Data Pipeline

A **fully serverless**, **event-driven** AWS pipeline that ingests site-level telemetry, enriches it in real time, flags anomalies, and exposes the cleansed data through a FastAPI endpoint. The stack is perfect for demos, take-home assignments, or green-field prototypes where infrastructure-as-code, CI/CD, and automated testing matter.:contentReference[oaicite:0]{index=0}  

---

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Environment Variables](#environment-variables)
5. [Local Simulation](#local-simulation)
6. [Deploy to AWS](#deploy-to-aws)
7. [Smoke Tests & Unit Tests](#tests)
8. [CI/CD (--> GitHub Actions)](#cicd)
9. [Cleanup / Teardown](#cleanup)
10. [Results & Deliverables](#results--deliverables)
11. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## 🛫 Prerequisites  <a id="prerequisites"></a>

| Tool | Why it’s needed | Version |
|------|-----------------|---------|
| **AWS CLI** | Provision & smoke-test AWS resources | ≥ 2.15 |
| **Terraform** | Infrastructure as Code | ≥ 1.5 |
| **Python** | Lambda runtime & local dev | 3.11 |
| **Git** | Source control | latest |
| **jq** | Pretty-print JSON in shell examples | latest |

> Ensure your AWS credentials (`aws configure`) can create **S3, Lambda, DynamoDB, SNS, IAM, API Gateway, CloudWatch** resources.:contentReference[oaicite:1]{index=1}  

---

# 🚀 Quick Start  <a id="quick-start"></a>

### 1 — Clone
```bash
git clone https://github.com/NikhilBhoopalam/data-pipeline-project.git
cd data-pipeline-project
```

### 2 — Create & Activate Virtualenv
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 3 —  Local API Hot-Reload
```bash
uvicorn api.app:app --reload --port 8000
```

### 4 —   Run All Unit Tests
```bash
pytest -q
```
Uses Moto to mock AWS → zero cloud bill during test runs.

Project Structure <a id="project-structure"></a>
```bash
.
├── api/                 # FastAPI application (deployed via API Gateway + Lambda)
├── data_feed/           # Simulation script to push JSON records to S3
├── lambda_function/     # Processor Lambda: S3 ➜ DynamoDB (+ SNS alerts)
├── terraform/           # Complete IaC for S3, DynamoDB, Lambdas, API GW, SNS
├── tests/               # Pytest unit tests (Moto-powered)
├── visualization/       # Sample charts (PNG) + Matplotlib helper
├── requirements*.txt    # Runtime & dev dependency pins
└── README.md            # You’re reading it 😉

```

### Environment Variables <a id="environment-variables"></a>

``` bash

| Variable     | Who uses it            | Default      | Notes                                   |
| ------------ | ---------------------- | ------------ | --------------------------------------- |
| `AWS_REGION` | All Lambdas & CLI      | `us-east-1`  | Change if you want to  deploy elsewhere |
| `DDB_TABLE`  | API & Processor Lambda | `EnergyData` | DynamoDB table name                     |
| `SNS_TOPIC`  | Processor Lambda       | *(none)*     | ARN for anomaly alerts                  |
| `LOG_LEVEL`  | All Python services    | `INFO`       | Optional override                       |
```

### Deploy to AWS (One Command) <a id="deploy-to-aws"></a>
``` bash

cd terraform
# 0. (Optional) edit backend.bucket & region for your own Terraform state
terraform init
terraform apply -auto-approve
```
### Outputs to capture:

``` bash 

export BUCKET_NAME=$(terraform output -raw data_feed_bucket_bucket)
export TABLE_NAME=$(terraform output -raw dynamodb_table_name)
export API_ENDPOINT=$(terraform output -raw api_endpoint)
export ALERT_TOPIC_ARN=$(terraform output -raw alert_topic_arn)   # optional SNS
```

# ✅ Tests <a id="tests"></a>

### Smoke-Test End-to-End

``` bash

echo '{"site_id":"cli","timestamp":"2025-06-14T12:00:00Z","energy_generated_kwh":50,"energy_consumed_kwh":10}' > test.json
aws s3 cp test.json s3://$BUCKET_NAME/test.json
curl "$API_ENDPOINT/records?site_id=cli" | jq .

```
### Unit Tests

```bash
pytest --cov .
```
Moto stubs S3, DynamoDB, SNS; coverage target ≥ 90 %.

# CI/CD <a id="cicd"></a>
```bash 
.github/workflows/deploy.yml
```
    -> Lint → Unit-Test → Terraform Apply.

    -> On main push, a badge turns green when the stack and tests succeed:
``` bash 

![](https://github.com/NikhilBhoopalam/data-pipeline-project/actions/workflows/deploy.yml/badge.svg)
```

# Cleanup <a id="cleanup"></a>
``` bash
cd terraform
terraform destroy -auto-approve
aws s3 rb "s3://$BUCKET_NAME" --force || true
```
All resources (S3, DynamoDB, Lambdas, API Gateway, SNS) are deleted; no lingering cost items.








| Deliverable                                     | Proof                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **S3 ➜ Lambda ➜ DynamoDB** flow                 | Uploading `test.json` writes a row with computed `net_energy_kwh` + `anomaly` flag         |
| **API** (`GET /records`, `GET /anomalies`)      | Accessible via `$API_ENDPOINT` in stack outputs                                            |
| **Custom Metric** `EnergyPipeline/AnomalyCount` | Visible under CloudWatch → Metrics                                                         |
| **SNS Alert** e-mail on anomaly                 | Subscribe to `$ALERT_TOPIC_ARN` and trigger with negative kWh                              |
| **Unit-Test Coverage > 90 %**                   | `pytest --cov` summary                                                                     |
| **CI Badge**                                    | ![](https://github.com/NikhilBhoopalam/data-pipeline-project/actions/workflows/deploy.yml/badge.svg) |


Example record (after Lambda processing):

```bash
{
  "site_id": "cli",
  "timestamp": "2025-06-14T12:00:00Z",
  "energy_generated_kwh": 50,
  "energy_consumed_kwh": 10,
  "net_energy_kwh": 40,
  "anomaly": false
}

```


