from aws_cdk import (
    aws_lambda as lambda_,
    Duration,
    aws_iam as iam,
    Stack,
)
from constructs import Construct
from .construct.Invoke_agent.invoke_agent_api_gateway import AgentApiGateway
from .construct.Invoke_agent.convo_logs_dynemodb import ChatAgentLogTable

class AgentInvokerLambda(Construct):
    def __init__(self, scope: Construct, construct_id: str, agent_id: str, agent_alias_id: str) -> None:
        super().__init__(scope, construct_id)

        # Create the DynamoDB table for chat logs
        self.table = ChatAgentLogTable(
            self,
            "ChatAgentLogTable"
        )

        # Environment variables for the Lambda
        lambda_env = {
            "AGENT_ID": agent_id,
            "AGENT_ALIAS_ID": agent_alias_id,
            "REGION_NAME": "us-east-1",
            "LOG_TABLE_NAME": self.table.table.table_name
        }

        # Create Lambda role without logging permissions
        lambda_role = iam.Role(
            self,
            "AgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # Grant permission to write to the DynamoDB table
        self.table.table.grant_write_data(lambda_role)

        # Create Lambda function
        self.lambda_function = lambda_.Function(
            self,
            "AgentInvokerLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="invoke_agent.handler",
            code=lambda_.Code.from_asset("src/lambda"),  
            timeout=Duration.seconds(60),
            environment=lambda_env,
            memory_size=256,
            role=lambda_role
        )

        # Grant permission to invoke Bedrock agent
        account_id = Stack.of(self).account
        self.lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeAgent"],
                resources=["*"]
    )
)

        # Instantiate the API Gateway construct, passing the Lambda function
        self.api_gateway = AgentApiGateway(
            self,
            "AgentApiGateway",
            lambda_function=self.lambda_function
        )