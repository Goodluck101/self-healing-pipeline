# 

import json
import boto3
import os
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
code_pipeline = boto3.client('codepipeline')
cloudwatch = boto3.client('cloudwatch')
# Check your Bedrock model availability region
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('BEDROCK_REGION', 'us-east-1'))

def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event, indent=2))

    # 1. Extract Alarm information from the CloudWatch event
    try:
        alarm_name = event['detail']['alarmData']['alarmName']
        new_state = event['detail']['alarmData']['state']['value']
        reason = event['detail']['alarmData']['state']['reason']

        # Only proceed if the alarm is in ALARM state
        if new_state != 'ALARM':
            logger.info(f"Alarm {alarm_name} is in {new_state} state. No action needed.")
            return {'statusCode': 200, 'body': json.dumps('No action taken.')}

    except KeyError as e:
        logger.error(f"Error parsing event: {e}")
        return {'statusCode': 400, 'body': json.dumps('Malformed event data.')}

    # 2. Get pipeline name from environment variable (set by Terraform)
    pipeline_name = os.getenv('PIPELINE_NAME')
    if not pipeline_name:
        logger.error("PIPELINE_NAME environment variable not set")
        return {'statusCode': 500, 'body': json.dumps('Pipeline name not configured.')}

    # 3. Use Bedrock to analyze the situation and recommend action
    try:
        prompt = f"""
        Human: An AWS CloudWatch alarm '{alarm_name}' has triggered with reason: '{reason}'. 
        This alarm monitors a banking API deployment on Kubernetes. The most likely cause is a recent code deployment that introduced a bug causing HTTP 500 errors.
        Should we roll back the deployment? Respond ONLY with a valid JSON object in this exact format:
        {{
            "analysis": "A one-sentence summary of the likely problem based on the reason.",
            "recommendation": "ROLLBACK" 
        }}

        Assistant:
        """
        
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 500,
            "temperature": 0.5,
            "top_p": 1,
        })
        
        model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-v2')
        
        bedrock_response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(bedrock_response.get('body').read())
        completion = response_body.get('completion')
        logger.info(f"Bedrock analysis: {completion}")

        # Parse the JSON response from Bedrock
        advice = json.loads(completion)
        if advice['recommendation'] != 'ROLLBACK':
            logger.info("Bedrock did not recommend a rollback. Stopping.")
            return {'statusCode': 200, 'body': json.dumps('Rollback not recommended by AI.')}

    except Exception as e:
        logger.error(f"Error using Bedrock: {e}. Proceeding with rollback based on alarm alone.")

    # 4. Initiate Rollback in CodePipeline
    try:
        # Find the latest execution of the pipeline
        executions = code_pipeline.list_pipeline_executions(
            pipelineName=pipeline_name,
            maxResults=1
        )
        
        if not executions['pipelineExecutionSummaries']:
            logger.error("No pipeline executions found")
            return {'statusCode': 404, 'body': json.dumps('No pipeline executions found.')}
            
        latest_execution = executions['pipelineExecutionSummaries'][0]
        latest_execution_id = latest_execution['pipelineExecutionId']
        latest_status = latest_execution['status']

        # Only rollback if the latest execution was successful (which caused the problem)
        if latest_status == 'Succeeded':
            logger.info(f"Initiating rollback for execution: {latest_execution_id}")
            # This starts a new execution, which by default uses the last good artifact
            rollback_response = code_pipeline.start_pipeline_execution(
                name=pipeline_name
            )
            logger.info(f"Rollback execution started: {rollback_response['pipelineExecutionId']}")
            
            message = f"🚨 ALARM: {alarm_name}. 🤖 AI-initiated rollback started. Execution ID: {rollback_response['pipelineExecutionId']}"
            
            # Send notification (you can integrate with SNS here)
            logger.info(f"ACTION: {message}")
            
        else:
            message = f"Alarm {alarm_name} triggered but latest pipeline execution was {latest_status}. Manual investigation needed."
            logger.info(message)

    except Exception as e:
        logger.error(f"Error initiating rollback: {e}")
        message = f"Failed to initiate rollback for alarm {alarm_name}. Error: {str(e)}"
        return {'statusCode': 500, 'body': json.dumps(message)}

    return {
        'statusCode': 200,
        'body': json.dumps(message)
    }