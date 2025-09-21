# Data source for AWS Availability Zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Data source for EKS cluster auth token
data "aws_eks_cluster_auth" "this" {
  name = module.eks.cluster_name
}

# Create the VPC for the EKS cluster using the official AWS module (best practice)
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2) # Use 2 AZs
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true # Cost-saving for demo
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }

  tags = var.tags
}

# Create the EKS cluster using the official AWS module (best practice)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.eks_cluster_name
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    demo-node-group = {
      min_size     = 1
      max_size     = 3
      desired_size = 2

      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
  }

  tags = var.tags
}

# Create the ECR Repository
resource "aws_ecr_repository" "app" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# Create the CodeBuild Project
resource "aws_codebuild_project" "self_healing_build" {
  name          = var.codebuild_project_name
  description   = "Builds and deploys the self-healing bank app to EKS"
  service_role  = aws_iam_role.codebuild_role.arn
  build_timeout = 10

  # Environment to run the build in
  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true # Necessary for Docker builds

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }
    environment_variable {
      name  = "EKS_CLUSTER_NAME"
      value = module.eks.cluster_name
    }
  }

  # The source code and build instructions are in the connected repository
  source {
    type            = "CODEPIPELINE"
    buildspec       = "buildspec.yml" # Path in your source repo
    git_clone_depth = 1
  }

  artifacts {
    type = "CODEPIPELINE"
  }

  tags = var.tags
}

# Create the CodePipeline
resource "aws_codepipeline" "self_healing_pipeline" {
  name     = var.codepipeline_name
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = replace(var.github_repo_url, "https://github.com/", "") # Converts URL to "owner/repo"
        BranchName       = var.github_branch
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.self_healing_build.name
      }
    }
  }

  # The Deploy stage is handled within the CodeBuild project's buildspec
  tags = var.tags
}

# Create the Lambda Function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../lambda-rollback" # Path to your Lambda function code
  output_path = "${path.module}/lambda_package.zip"
}

resource "aws_lambda_function" "rollback" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30

  environment {
    variables = {
      PIPELINE_NAME    = aws_codepipeline.self_healing_pipeline.name
      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }

  tags = var.tags
}

# Create the CloudWatch Anomaly Detection Alarm
resource "aws_cloudwatch_metric_alarm" "bank_api_5xx_anomaly" {
  alarm_name          = "Bank-API-High-5XX-Errors"
  comparison_operator = "GreaterThanUpperThreshold"
  evaluation_periods  = 1
  threshold_metric_id = "e1"
  alarm_description   = "Triggers if 5XX errors from the Bank API ELB are anomalously high (indicating a bad deployment)."

  metric_query {
    id          = "e1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 100)"
    label       = "ErrorCount (Expected)"
    return_data = "true"
  }

  metric_query {
    id = "m1"

    metric {
      metric_name = "HTTPCode_ELB_5XX_Count"
      namespace   = "AWS/ApplicationELB"
      period      = 60
      stat        = "Sum"
      dimensions = {
        # These dimensions will be populated by the LoadBalancer created by Kubernetes.
        # We use a wildcard to match any LoadBalancer in the account. For a more precise alarm,
        # you would create this after the first deployment and get the exact LB name, then import it into Terraform.
        LoadBalancer = "*"
      }
    }
  }

  alarm_actions = [
    aws_lambda_function.rollback.arn,
    # Add an SNS topic ARN here if you want notifications
  ]

  tags = var.tags
}

# Supporting Resources: S3 Bucket for CodePipeline artifacts, CodeStar Connection for GitHub
resource "aws_s3_bucket" "codepipeline_artifacts" {
  bucket        = "${var.project_name}-artifacts-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # For easy demo cleanup

  tags = var.tags
}

resource "aws_s3_bucket_acl" "codepipeline_artifacts_acl" {
  bucket = aws_s3_bucket.codepipeline_artifacts.id
  acl    = "private"
}

resource "aws_codestarconnections_connection" "github" {
  name          = "${var.project_name}-github-connection"
  provider_type = "GitHub"
}

data "aws_caller_identity" "current" {}

resource "aws_lambda_function" "rollback" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30

  environment {
    variables = {
      PIPELINE_NAME    = aws_codepipeline.self_healing_pipeline.name
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_REGION   = "us-east-1"  # Or make this a variable
    }
  }

  tags = var.tags
}