# sns.tf
resource "aws_sns_topic" "alarm_notifications" {
  name = "${var.project_name}-alarm-notifications"  # Use variable for consistency
  
  tags = merge(var.tags, {
    Purpose = "CloudWatch Alarm Notifications"
  })
}

# Email subscription - good for testing
resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.alarm_notifications.arn
  protocol  = "email"
  endpoint  = "goody.devops@gmail.com"
  
  # Add depends_on to ensure policy exists before subscription
  depends_on = [aws_sns_topic_policy.alarm_notifications_policy]
}

# IAM policy to allow CloudWatch to publish to SNS - IMPROVED VERSION
resource "aws_sns_topic_policy" "alarm_notifications_policy" {
  arn = aws_sns_topic.alarm_notifications.arn
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        },
        Action = "sns:Publish",
        Resource = aws_sns_topic.alarm_notifications.arn,
        Condition = {
          ArnLike = {
            "aws:SourceArn" = "arn:aws:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:*"
          }
        }
      }
    ]
  })
  
  # Ensure the topic exists before creating policy
  depends_on = [aws_sns_topic.alarm_notifications]
}