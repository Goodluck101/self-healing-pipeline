import json
import boto3
import os
import logging
import subprocess
import base64
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
codepipeline = boto3.client('codepipeline')
sns = boto3.client('sns')
eks = boto3.client('eks')

def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event, indent=2))

    # Extract pipeline information from the event
    try:
        pipeline_name = event['detail']['pipeline']
        execution_id = event['detail']['execution-id']
        state = event['detail']['state']

        logger.info(f"Pipeline: {pipeline_name}, Execution: {execution_id}, State: {state}")

        # Only proceed if this is a successful build completion
        if state != 'SUCCEEDED':
            logger.info(f"Pipeline execution {execution_id} did not succeed. State: {state}")
            return {'statusCode': 200, 'body': json.dumps('Build not successful, skipping deployment.')}

    except KeyError as e:
        logger.error(f"Error parsing CodePipeline event: {e}")
        return {'statusCode': 400, 'body': json.dumps('Invalid CodePipeline event format.')}

    # Get environment variables
    eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')
    ecr_repository_url = os.getenv('ECR_REPOSITORY_URL')
    sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    if not all([eks_cluster_name, ecr_repository_url, sns_topic_arn]):
        logger.error("Missing required environment variables")
        return {'statusCode': 500, 'body': json.dumps('Missing required environment variables.')}

    try:
        # Get pipeline execution details to find the commit ID
        execution_details = codepipeline.get_pipeline_execution(
            pipelineName=pipeline_name,
            pipelineExecutionId=execution_id
        )

        # Extract source revision (commit ID) from the execution
        source_revision = None
        if 'sourceRevisions' in execution_details['pipelineExecution']:
            for revision in execution_details['pipelineExecution']['sourceRevisions']:
                if revision['actionName'] == 'Source':
                    source_revision = revision['revisionId']
                    break

        if not source_revision:
            logger.warning("Could not find source revision, using 'latest' tag")
            image_tag = 'latest'
        else:
            # Use first 8 characters of commit hash as tag
            image_tag = source_revision[:8]

        logger.info(f"Using image tag: {image_tag}")

        # Send deployment started notification
        send_notification(sns_topic_arn, "🚀 DEPLOYMENT STARTED",
                         f"Starting deployment of {pipeline_name} execution {execution_id} to EKS cluster {eks_cluster_name}")

        # Configure kubectl for EKS
        configure_kubectl(eks_cluster_name, aws_region)

        # Update Kubernetes deployment with new image
        update_deployment(ecr_repository_url, image_tag)

        # Wait for deployment rollout
        wait_for_rollout()

        # Send success notification
        send_notification(sns_topic_arn, "✅ DEPLOYMENT SUCCESSFUL",
                         f"Successfully deployed {pipeline_name} execution {execution_id} to EKS cluster {eks_cluster_name}")

        return {
            'statusCode': 200,
            'body': json.dumps(f'Deployment completed successfully for execution {execution_id}')
        }

    except Exception as e:
        error_message = f"Deployment failed for {pipeline_name} execution {execution_id}: {str(e)}"
        logger.error(error_message)

        # Send failure notification
        send_notification(sns_topic_arn, "❌ DEPLOYMENT FAILED", error_message)

        return {
            'statusCode': 500,
            'body': json.dumps(error_message)
        }

def configure_kubectl(cluster_name, region):
    """Configure kubectl to connect to EKS cluster"""
    try:
        logger.info(f"Configuring kubectl for EKS cluster: {cluster_name}")

        # Get cluster details
        cluster = eks.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster['cluster']['endpoint']
        cluster_ca = cluster['cluster']['certificateAuthority']['data']

        # Create kubeconfig
        kubeconfig = f"""
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {cluster_ca}
    server: {cluster_endpoint}
  name: {cluster_name}
contexts:
- context:
    cluster: {cluster_name}
    user: {cluster_name}
  name: {cluster_name}
current-context: {cluster_name}
kind: Config
preferences: {{}}
users:
- name: {cluster_name}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
      - eks
      - get-token
      - --cluster-name
      - {cluster_name}
      - --region
      - {region}
"""

        # Write kubeconfig to file
        with open('/tmp/kubeconfig', 'w') as f:
            f.write(kubeconfig)

        # Set KUBECONFIG environment variable
        os.environ['KUBECONFIG'] = '/tmp/kubeconfig'

        logger.info("kubectl configured successfully")

    except Exception as e:
        logger.error(f"Failed to configure kubectl: {e}")
        raise

def update_deployment(ecr_repository_url, image_tag):
    """Update the Kubernetes deployment with new image"""
    try:
        logger.info(f"Updating deployment with image: {ecr_repository_url}:{image_tag}")

        # Read the deployment manifest
        with open('app/kubernetes/deployment.yaml', 'r') as f:
            deployment_yaml = f.read()

        # Replace the image placeholder
        updated_yaml = deployment_yaml.replace(
            'IMAGE_PLACEHOLDER',
            f'{ecr_repository_url}:{image_tag}'
        )

        # Write updated manifest
        with open('/tmp/deployment-updated.yaml', 'w') as f:
            f.write(updated_yaml)

        # Apply the deployment
        result = subprocess.run([
            'kubectl', 'apply', '-f', '/tmp/deployment-updated.yaml'
        ], capture_output=True, text=True, check=True)

        logger.info(f"kubectl apply result: {result.stdout}")

        # Also apply the service (in case it hasn't been applied yet)
        result = subprocess.run([
            'kubectl', 'apply', '-f', 'app/kubernetes/service.yaml'
        ], capture_output=True, text=True, check=True)

        logger.info(f"Service apply result: {result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl command failed: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Failed to update deployment: {e}")
        raise

def wait_for_rollout():
    """Wait for the deployment rollout to complete"""
    try:
        logger.info("Waiting for deployment rollout to complete")

        result = subprocess.run([
            'kubectl', 'rollout', 'status', 'deployment/simple-bank-api', '--timeout=300s'
        ], capture_output=True, text=True, check=True)

        logger.info(f"Rollout status: {result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Rollout failed: {e.stderr}")
        raise

def send_notification(topic_arn, subject, message):
    """Send notification via SNS"""
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"Notification sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")