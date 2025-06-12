############################
# Terraform settings
############################
terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket = "tf-state-data-pipeline-nikhil-20250610" # your unique state bucket
    key    = "energy-pipeline/terraform.tfstate"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source = "hashicorp/archive"
    }
  }
}

############################
# AWS Provider
############################
provider "aws" {
  region = "us-east-1"
}

############################
# Variables
############################
# In terraform/variables.tf you should have:
# variable "alert_topic_arn" {
#   description = "SNS topic ARN for anomaly alerts"
#   type        = string
#   default     = "arn:aws:sns:us-east-1:389595560995:EnergyAlerts"
# }

############################
# Random suffix for uniqueness
############################
resource "random_id" "suffix" {
  byte_length = 4
}

############################
# S3 bucket for incoming JSON files
############################
resource "aws_s3_bucket" "data_feed_bucket" {
  bucket        = "energy-feed-${random_id.suffix.hex}"
  force_destroy = true
}

############################
# DynamoDB table for processed records
############################
resource "aws_dynamodb_table" "energy_table" {
  name         = "EnergyData"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "site_id"
  range_key    = "timestamp"

  attribute {
    name = "site_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }

  # Optional: enable point-in-time recovery, TTL, tags, etc.
  # point_in_time_recovery {
  #   enabled = true
  # }
}

############################
# IAM Role for Processor Lambda (S3 -> DynamoDB + SNS)
############################
resource "aws_iam_role" "lambda_role" {
  name = "lambda-s3-dynamo-role-${random_id.suffix.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attach policies to the Processor Lambda role
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy_attachment" "s3_read" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}
resource "aws_iam_role_policy_attachment" "ddb_write" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}
resource "aws_iam_role_policy_attachment" "sns_publish" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}
# (Optionally tighten DynamoDB to PutItem only, but for now FullAccess works.)

############################
# Package Processor Lambda code as zip
############################
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda_function"
  output_path = "${path.module}/lambda.zip"
}

############################
# Processor Lambda function (S3 → DynamoDB + SNS alerts)
############################
resource "aws_lambda_function" "processor" {
  function_name = "ProcessEnergyData"
  runtime       = "python3.9"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      DDB_TABLE = aws_dynamodb_table.energy_table.name
      SNS_TOPIC = var.alert_topic_arn
    }
  }
}

############################
# Permission: allow S3 to invoke Processor Lambda on object creation
############################
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_feed_bucket.arn
}

resource "aws_s3_bucket_notification" "notify" {
  bucket = aws_s3_bucket.data_feed_bucket.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }
  depends_on = [aws_lambda_permission.allow_s3]
}
