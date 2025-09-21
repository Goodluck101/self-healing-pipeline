# variable "aws_region" {
#   description = "AWS region to deploy resources into"
#   type        = string
#   default     = "us-east-1"
# }

# variable "project_name" {
#   description = "Name of the project, used for resource naming and tagging"
#   type        = string
#   default     = "self-healing-bank-pipeline"
# }

# variable "github_repo_url" {
#   description = "URL of the GitHub repository containing the application code"
#   type        = string
# }

# variable "github_branch" {
#   description = "GitHub branch to trigger the pipeline from"
#   type        = string
#   default     = "main"
# }

# variable "tags" {
#   description = "A map of tags to add to all resources"
#   type        = map(string)
#   default = {
#     Project     = "SelfHealingDemo"
#     Environment = "Production"
#     Terraform   = "true"
#     ManagedBy   = "CodePipeline"
#   }
# }


# AWS Configuration
variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project, used for resource naming and tagging"
  type        = string
  default     = "self-healing-bank-pipeline"
}

# GitHub Configuration
variable "github_repo_url" {
  description = "URL of the GitHub repository containing the application code"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to trigger the pipeline from"
  type        = string
  default     = "main"
}

# EKS Configuration
variable "eks_cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "self-healing-cicd-cluster"
}

# ECR Configuration
variable "ecr_repo_name" {
  description = "Name of the ECR repository for the application image"
  type        = string
  default     = "simple-bank-api-reg"
}

# CodeBuild Configuration
variable "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  type        = string
  default     = "self-healing-bank-build"
}

# CodePipeline Configuration
variable "codepipeline_name" {
  description = "Name of the CodePipeline"
  type        = string
  default     = "self-healing-bank-pipeline"
}

# Lambda Configuration
variable "lambda_function_name" {
  description = "Name of the self-healing Lambda function"
  type        = string
  default     = "self-healing-rollback-function"
}

# Bedrock Configuration
variable "bedrock_model_id" {
  description = "The model ID for Amazon Bedrock (e.g., anthropic.claude-v2)"
  type        = string
  default     = "anthropic.claude-v2"
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default = {
    Project     = "SelfHealingDemo"
    Environment = "Production"
    Terraform   = "true"
    ManagedBy   = "CodePipeline"
  }
}