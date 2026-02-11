terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "6.31.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "input_bucket" {
  bucket = "${var.project_name}-input-bucket-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "processed_bucket" {
  bucket = "${var.project_name}-processed-bucket-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "report_bucket" {
  bucket = "${var.project_name}-report-bucket-${random_id.bucket_suffix.hex}"
}

resource "aws_iam_role" "lambda_role" {
    name = "${var.project_name}lambda-role"
    
    assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
  
}
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}lambda-policy"
  role = aws_iam_role.lambda_role.id
   policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
            "${aws_s3_bucket.input_bucket.arn}",
            "${aws_s3_bucket.input_bucket.arn}/*",
            "${aws_s3_bucket.processed_bucket.arn}",
            "${aws_s3_bucket.processed_bucket.arn}/*",
            "${aws_s3_bucket.report_bucket.arn}",
            "${aws_s3_bucket.report_bucket.arn}/*",
        ] 
      },
      {
        Action=[
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        ]
        Effect="Allow"
        Resource="arn:aws:logs:*:*:*"
      },
      {
        Action="sns:Publish"
        Effect="Allow"
        Resource=aws_sns_topic.notifications.arn
      }
    ]
  })
}

resource "aws_lambda_function" "data_processor" {
    filename = "../lambda/data_processor.zip"
    function_name = "${var.project_name}-processor"
    role = aws_iam_role.lambda_role.arn
    handler = "lambda_function.lambda_handler"
    runtime = "python3.11"
    timeout = 60

  environment {
    variables = {
        PROCESSED_BUCKET = aws_s3_bucket.processed_bucket.id
    }
  }
  
}
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_bucket.arn
}

resource "aws_s3_bucket_notification" "input_notification" {
    bucket = aws_s3_bucket.input_bucket.id

    lambda_function {
      lambda_function_arn = aws_lambda_function.data_processor.arn
      events = ["s3:ObjectCreated:*"]
      filter_suffix = ".json"
    }

    lambda_function {
      lambda_function_arn = aws_lambda_function.data_processor.arn
      events=["s3:ObjectCreated:*"]
      filter_suffix = ".csv"
    }
    depends_on = [aws_lambda_permission.allow_s3]

}

resource "aws_lambda_function" "report_generator" {
  filename      = "../lambda/report_generator.zip"
  function_name = "${var.project_name}-generator"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  environment {
    variables = {
        PROCESSED_BUCKET=aws_s3_bucket.processed_bucket.id
        REPORTS_BUCKET=aws_s3_bucket.report_bucket.id
        SNS_TOPIC_ARN=aws_sns_topic.notifications.arn
    }
  }
}

resource "aws_sns_topic" "notifications" {
    name="${var.project_name}-notifications"  
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_cloudwatch_event_rule" "daily_report" {
  name        = "${var.project_name}-daily"
  description = "trigger daily post"
  schedule_expression = "cron(0 8 * * ? *)"
  }

resource "aws_cloudwatch_event_target" "report_target" {
  rule      = aws_cloudwatch_event_rule.daily_report.name
  target_id = "ReportLambda"
  arn       = aws_lambda_function.report_generator.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.report_generator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_report.arn
}
output "input_bucket" {
    value = aws_s3_bucket.input_bucket.id
}
output "processed_bucket" {
    value = aws_s3_bucket.processed_bucket.id
}
output "report_bucket" {
    value = aws_s3_bucket.report_bucket.id
}