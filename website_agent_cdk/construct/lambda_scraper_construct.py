from aws_cdk import (
    aws_lambda as lambda_,
    Duration,
    aws_iam as iam,
    aws_s3 as s3,
    DockerImage,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion, BundlingOptions

class DataScraper(Construct):
    def __init__(self, scope: Construct, construct_id: str, bucket_name: str, knowledge_base_id: str, data_source_id: str) -> None:
        super().__init__(scope, construct_id)

        # Load environment variables
        lambda_env = {
            "BUCKET_NAME": bucket_name,
            "GITHUB_USER": "jank601",
            "KNOWLEDGE_BASE_ID": knowledge_base_id,
            "DATA_SOURCE_ID": data_source_id
        }

        # Use the published Git layer ARN (adjust the ARN to your region if necessary)
        git_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "GitLayer",
            "arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8"
        )


        # Python packages layer with bundling options
        python_layer = PythonLayerVersion(
            self,
            "PythonLayer",
            entry="lambda_layers",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Layer with Python packages",
            bundling=BundlingOptions(
                image=DockerImage.from_registry("public.ecr.aws/sam/build-python3.12"),
                command=[
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output/python"
                ],
                user="root"
            )
        )

        # Create Lambda function
        self.lambda_function = lambda_.Function(
            self,
            "website-scraper-lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="web_crawler.lambda_handler",
            code=lambda_.Code.from_asset("src/lambda"),
            layers=[git_layer, python_layer],
            timeout=Duration.seconds(60),
            environment=lambda_env,
            memory_size=512
        )

        # Grant S3 permissions
        bucket = s3.Bucket.from_bucket_name(self, "ImportedBucket", bucket_name)
        bucket.grant_read_write(self.lambda_function)

        account_id = Stack.of(self).account

        # Grant permission to invoke Bedrock runtime's converse API
        self.lambda_function.add_to_role_policy(
    iam.PolicyStatement(
        actions=["bedrock:InvokeModel"],
        resources=["arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0"]
    )
)
        self.lambda_function.add_to_role_policy(
    iam.PolicyStatement(
        actions=["bedrock:StartIngestionJob"],
        resources=[f"arn:aws:bedrock:us-east-1:{account_id}:knowledge-base/{knowledge_base_id}"]
    )
)
        
        self.lambda_function.add_to_role_policy(
    iam.PolicyStatement(
        actions=["bedrock:AssociateThirdPartyKnowledgeBase"],
        resources=[f"arn:aws:bedrock:us-east-1:{account_id}:knowledge-base/{knowledge_base_id}"]
    )
)
        
 # Schedule the Lambda to run once a week using EventBridge
        weekly_rule = events.Rule(
            self,
            "WeeklyRunRule",
            schedule=events.Schedule.cron(minute="0", hour="0", week_day="SUN")
        )
        weekly_rule.add_target(targets.LambdaFunction(self.lambda_function))