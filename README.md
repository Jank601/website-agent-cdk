# Website Agent CDK Project

This project deploys a complete architecture for a website chatbot powered by AWS Bedrock Agents. It uses AWS CDK to define and provision all necessary infrastructure.

## Architecture Overview

The system consists of:

1. **AWS Bedrock Agent**: Provides conversational AI capabilities with access to a knowledge base.
2. **Knowledge Base**: Stores and retrieves information from various data sources.
3. **Data Ingestion Pipeline**: Automatically scrapes GitHub repositories, processes files, and ingests them into the knowledge base.
4. **Lambda Functions**: Handle API requests, custom chunking, and data processing.
5. **API Gateway**: Exposes a secure REST API for invoking the agent.
6. **DynamoDB**: Stores conversation logs.

## Prerequisites

- AWS Account with access to Bedrock
- Pinecone Vector Database account
- Python 3.12+
- AWS CDK v2
- Node.js 14+

## Setup

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd website-agent-cdk
   ```

2. **Create a `config.json` file in the project root**:
   ```json
   {
     "pineconeApiKey": "your-pinecone-api-key",
     "pineconeEndpoint": "your-pinecone-endpoint"
   }
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Install AWS CDK (if not already installed)**:
   ```
   npm install -g aws-cdk
   ```

5. **Bootstrap your AWS environment**:
   ```
   cdk bootstrap
   ```

6. **Create Lambda Layer directory structure**:
   ```
   mkdir -p lambda_layers
   touch lambda_layers/requirements.txt
   ```

7. **Add required Python packages to `lambda_layers/requirements.txt`**:
   ```
   GitPython
   requests
   ```

## Deployment

Deploy the stack to your AWS account:

```
cdk deploy
```

After deployment, the CDK outputs will include:
- API Gateway URL
- Agent ID
- Agent Alias ID

## Components

### Agent Construct (`agent_construct.py`)
Sets up the AWS Bedrock Agent with system prompts, IAM roles, and knowledge base connections.

### Knowledge Base Construct (`kb_consruct.py`)
Creates a vector knowledge base using Pinecone as the storage backend.

### Data Source Construct (`data_source_construct.py`)
Configures data sources for the knowledge base with custom chunking capabilities.

### Lambda Functions
- **Invoke Agent Lambda (`invoke_agent.py`)**: Handles API requests and invokes the Bedrock Agent.
- **Custom Chunking Lambda (`CustomChunking.py`)**: Processes and chunks text data for the knowledge base.
- **Web Crawler Lambda (`web_crawler.py`)**: Scrapes GitHub repositories for content.

### API Gateway (`invoke_agent_api_gateway.py`)
Creates a secure REST API with usage plans and API key authentication.

### Supporting Constructs
- **DynamoDB Table (`convo_logs_dynemodb.py`)**: Stores conversation logs.
- **S3 Buckets**: Store raw and processed data.
- **Pinecone Secret**: Stores API keys securely.

## Usage

### Invoking the Agent via API

Make a POST request to the API Gateway endpoint with the following JSON body:

```json
{
  "input_text": "Your question here",
  "sessionId": "optional-session-id"
}
```

Headers:
```
x-api-key: YOUR_API_KEY
Content-Type: application/json
```

### Data Scraping

The system automatically scrapes GitHub repositories weekly (configurable in `lambda_scraper_construct.py`). 
To manually trigger a scrape, invoke the scraper Lambda function via the AWS Console or CLI.

## Customization

### Agent Instructions

To update the agent instructions, modify the `agent_instructions` string in `agent_construct.py`.

### Knowledge Base Configuration

Modify `kb_consruct.py` to adjust:
- Embedding model
- Vector database configuration
- IAM permissions

### Data Processing

The custom chunking strategy can be modified in `CustomChunking.py`.

## Security

This stack includes:
- IAM roles with least privilege principle
- API Gateway with API key authentication
- DynamoDB for secure logging
- Secrets Manager for storing sensitive keys

## Troubleshooting

- Check CloudWatch Logs for each Lambda function
- Verify IAM permissions for Bedrock access
- Ensure Pinecone credentials are correct in `config.json`