from aws_cdk import (
    aws_apigateway as apigw,
    CfnOutput,
    aws_lambda as lambda_,
)
from constructs import Construct
import secrets

class AgentApiGateway(Construct):
    def __init__(self, scope: Construct, construct_id: str, lambda_function: lambda_.IFunction) -> None:
        super().__init__(scope, construct_id)

        # Create API Gateway
        self.rest_api = apigw.RestApi(
            self,
            "AgentApi",
            rest_api_name="BedrockAgentApi"
        )

        # Create an API key
        self.api_key = apigw.ApiKey(
            self,
            "AgentApiKey",
            description="API key for Bedrock agent endpoint"
        )

        # Create a usage plan with daily quota of 100
        self.usage_plan = apigw.UsagePlan(
            self,
            "AgentUsagePlan",
            name="AgentUsagePlan",
            api_stages=[{"api": self.rest_api, "stage": self.rest_api.deployment_stage}],
            quota=apigw.QuotaSettings(limit=100, period=apigw.Period.DAY)
        )

        # Associate the API key with the usage plan
        self.usage_plan.add_api_key(self.api_key)

        # Create a resource and method with API key required
        resource = self.rest_api.root.add_resource("invoke-agent")
        resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_function),
            api_key_required=True
        )

        CfnOutput(
            self,
            "ApiEndpointOutput",
            value=f"{self.rest_api.url}invoke-agent",
            description="API Gateway endpoint URL for invoking the agent"
        )