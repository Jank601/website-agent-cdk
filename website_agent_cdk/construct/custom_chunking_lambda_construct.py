from constructs import Construct
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration,
)

class CustomChunkingLambda(Construct):
    def __init__(self, scope: Construct, id: str, input_bucket_arn: str, output_bucket_arn: str, **kwargs):
        super().__init__(scope, id)

        # Create Lambda execution role
        lambda_role = iam.Role(
            self,
            "custom_chunking_lambda_role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Grant read access to the input bucket
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    input_bucket_arn,
                    f"{input_bucket_arn}/*"
                ]
            )
        )

        # Grant read/write/delete access to the output bucket
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                resources=[
                    output_bucket_arn,
                    f"{output_bucket_arn}/*"
                ]
            )
        )

        # Create Lambda function
        self.lambda_function = lambda_.Function(
            self,
            "custom_chunking_lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(15),
            memory_size=1024,
            handler="CustomChunking.lambda_handler",
            code=lambda_.Code.from_asset("src/Lambda"),
            role=lambda_role,
        )