from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)
from constructs import Construct

class ChatAgentLogTable(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create the DynamoDB table for chat logs
        self.table = dynamodb.Table(
            self, "ChatAgentLogTable",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
