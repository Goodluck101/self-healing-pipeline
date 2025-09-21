output "eks_cluster_name" {
  description = "The name of the created EKS cluster"
  value       = module.eks.cluster_name
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.app.repository_url
}

output "how_to_configure_kubectl" {
  description = "Command to update your kubeconfig for the new EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}
