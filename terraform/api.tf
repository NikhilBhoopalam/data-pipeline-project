############################
# API Lambda IAM Role & Policies
############################
resource "aws_iam_role" "api_lambda_role" {
  name = "lambda-api-role-${random_id.suffix.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attach minimal policies for DynamoDB read only on our table
resource "aws_iam_role_policy" "api_dynamodb_read" {
  name = "lambda-ddb-read-${random_id.suffix.hex}"
  role = aws_iam_role.api_lambda_role.name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.energy_table.arn
      }
    ]
  })
}

# Basic Lambda execution permission
resource "aws_iam_role_policy_attachment" "api_lambda_basic" {
  role       = aws_iam_role.api_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

############################
# API Lambda function (FastAPI via Mangum)
############################
resource "aws_lambda_function" "api_handler" {
  function_name = "EnergyDataAPIHandler"
  runtime       = "python3.9"
  handler       = "api.app.handler" # in api/app.py: handler = Mangum(app)
  role          = aws_iam_role.api_lambda_role.arn

  # CI must place the zip here before terraform apply:
  filename         = "${path.module}/api_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/api_lambda.zip")

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      DDB_TABLE = aws_dynamodb_table.energy_table.name
    }
  }
}

############################
# API Gateway HTTP API
############################
resource "aws_apigatewayv2_api" "http_api" {
  name          = "EnergyDataAPI-${random_id.suffix.hex}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api_handler.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_records" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /records"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_anomalies" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /anomalies"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gw_invoke" {
  statement_id  = "AllowInvokeFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  # Optionally restrict source_arn:
  # source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

############################
# Output API endpoint (will be picked up by CI smoke tests)
############################
output "api_endpoint" {
  description = "HTTP API endpoint for EnergyDataAPI"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}
