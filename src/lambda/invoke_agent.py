import json
import boto3
import uuid
import datetime
import threading
from botocore.exceptions import ClientError
import os

# Response formatting class
class ResponseFormatter:
    @staticmethod
    def success(message, session_id):
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': message,
                'sessionId': session_id
            })
        }

    @staticmethod
    def error(error_message, status_code=500):
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': error_message
            })
        }

def log_to_dynamodb(session_id, question, response):
    """
    Writes the log to DynamoDB with separate attributes:
    - session_id (partition key)
    - timestamp (sort key)
    - question
    - response
    """
    try:
        table_name = os.environ.get('LOG_TABLE_NAME')
        if not table_name:
            print("LOG_TABLE_NAME environment variable not set")
            return
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        # Generate the timestamp
        timestamp = datetime.datetime.utcnow().isoformat()
        item = {
            'session_id': session_id,  # Partition key
            'timestamp': timestamp,    # Sort key
            'question': question,
            'response': response
        }
        table.put_item(Item=item)
    except Exception as e:
        print(f"Error logging to DynamoDB: {str(e)}")

def handler(event, context):
    try:
        # Validate and parse the request body
        if 'body' not in event:
            return ResponseFormatter.error('Missing body in request', 400)

        body = event['body']
        if isinstance(body, str):
            body = json.loads(body)

        input_text = body.get('input_text', '').strip()
        session_id = body.get('sessionId', str(uuid.uuid4()))

        if not input_text:
            return ResponseFormatter.error('Empty message provided', 400)

        # Get agent details from environment variables
        agent_id = os.environ['AGENT_ID']
        agent_alias_id = os.environ['AGENT_ALIAS_ID']
        region_name = os.environ['REGION_NAME']

        # Invoke the Bedrock Agent
        agent_response, new_session_id = invoke_bedrock_agent(
            agent_id, agent_alias_id, session_id, input_text, region_name
        )

        # Asynchronously log the question and response after sending the response
        threading.Thread(
            target=log_to_dynamodb, 
            args=(session_id, input_text, agent_response)
        ).start()

        return ResponseFormatter.success(agent_response, new_session_id or session_id)

    except json.JSONDecodeError:
        return ResponseFormatter.error('Invalid JSON in request body', 400)
    except ClientError as e:
        print(f"AWS Service error: {str(e)}")
        return ResponseFormatter.error('Service temporarily unavailable', 503)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return ResponseFormatter.error('Internal server error', 500)

def invoke_bedrock_agent(agent_id, agent_alias_id, session_id, input_text, region_name):
    try:
        # Initialize Bedrock Agent Runtime client
        bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=region_name)

        # Invoke the agent
        response = bedrock_agent.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=False 
        )

        # Extract completion from response
        completion = ""
        for event in response.get('completion', []):
            chunk = event.get('chunk', {})
            if 'bytes' in chunk:
                completion += chunk['bytes'].decode('utf-8')

        new_session_id = response.get('sessionId')
        return completion, new_session_id

    except ClientError as e:
        print(f"Couldn't invoke agent: {str(e)}")
        raise
    except Exception as e:
        print(f"Error parsing agent response: {str(e)}")
        raise