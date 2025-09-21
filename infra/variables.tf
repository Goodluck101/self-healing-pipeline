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

variable "github_repo_url" {
  description = "URL of the GitHub repository containing the application code"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to trigger the pipeline from"
  type        = string
  default     = "main"
}

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
