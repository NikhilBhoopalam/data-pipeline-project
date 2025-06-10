variable "alert_topic_arn" {
  description = "SNS topic ARN for anomaly alerts"
  type        = string
  default     = "arn:aws:sns:us-east-1:389595560995:EnergyAlerts"
}
