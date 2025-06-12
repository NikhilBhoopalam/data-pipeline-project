output "bucket_name" {
  description = "Name of the S3 bucket for data feed"
  value       = aws_s3_bucket.data_feed_bucket.bucket
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.energy_table.name
}

output "lambda_function_name" {
  description = "Name of the Processor Lambda function"
  value       = aws_lambda_function.processor.function_name
}

# API endpoint output lives in api.tf via its own output "api_endpoint"
# No need to duplicate here.
