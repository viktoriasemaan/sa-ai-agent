terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
}

resource "aws_kinesis_stream" "data_stream" {
  name             = "application-data-stream"
  shard_count      = 1
  retention_period = 24
}

resource "aws_lambda_function" "data_processor" {
  filename      = "lambda_function.zip"
  function_name = "data-processor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "nodejs14.x"
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda-kinesis-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_kinesis" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_s3_bucket" "data_lake" {
  bucket = "my-application-data-lake"
}

resource "aws_glue_catalog_database" "data_catalog" {
  name = "application_data_catalog"
}

resource "aws_glue_crawler" "s3_crawler" {
  database_name = aws_glue_catalog_database.data_catalog.name
  name          = "s3-data-crawler"
  role          = aws_iam_role.glue_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.bucket}"
  }
}

resource "aws_iam_role" "glue_role" {
  name = "glue-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
  role       = aws_iam_role.glue_role.name
}

resource "aws_glue_job" "etl_job" {
  name     = "etl-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.bucket}/scripts/etl_job.py"
  }
}

resource "aws_redshift_cluster" "data_warehouse" {
  cluster_identifier = "data-warehouse"
  database_name      = "analytics"
  master_username    = "admin"
  master_password    = "Password123!"
  node_type          = "dc2.large"
  cluster_type       = "single-node"
}

resource "aws_athena_database" "analytics" {
  name   = "analytics"
  bucket = aws_s3_bucket.data_lake.bucket
}

resource "aws_athena_workgroup" "analytics" {
  name = "analytics-workgroup"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.bucket}/athena-results/"
    }
  }
}

resource "aws_quicksight_account_subscription" "quicksight" {
  account_name        = "my-analytics-account"
  authentication_method = "IAM_AND_QUICKSIGHT"
  edition             = "ENTERPRISE"
  notification_email  = "admin@example.com"
}

resource "aws_sfn_state_machine" "data_workflow" {
  name     = "data-processing-workflow"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    StartAt = "IngestData"
    States = {
      IngestData = {
        Type     = "Task"
        Resource = "arn:aws:states:::kinesis:putRecord"
        Next     = "ProcessData"
      }
      ProcessData = {
        Type     = "Task"
        Resource = aws_lambda_function.data_processor.arn
        Next     = "CrawlData"
      }
      CrawlData = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startCrawler"
        Parameters = {
          Name = aws_glue_crawler.s3_crawler.name
        }
        Next = "TransformData"
      }
      TransformData = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun"
        Parameters = {
          JobName = aws_glue_job.etl_job.name
        }
        End = true
      }
    }
  })
}

resource "aws_iam_role" "step_functions_role" {
  name = "step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_functions_full_access" {
  policy_arn = "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess"
  role       = aws_iam_role.step_functions_role.name
}