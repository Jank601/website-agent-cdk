from aws_cdk import (
    aws_bedrock as bedrock,
    aws_iam as iam,
    Stack,
    Fn,
)
from constructs import Construct
from website_agent_cdk.construct.data_source_bucket import SourceDataBucket
from website_agent_cdk.construct.chunking_lambda_output__bucket_construct import ProcessedDataBucket
from website_agent_cdk.construct.custom_chunking_lambda_construct import CustomChunkingLambda
from website_agent_cdk.construct.lambda_scraper_construct import DataScraper


class DataSourceConstruct(Construct):
    def __init__(self, scope: Construct, id: str, knowledge_base_id: str,):
        super().__init__(scope, id)

        # Input S3 bucket for raw data storage
        self.input_bucket = SourceDataBucket(
            self,
            "InputBucket"
        )

        # Output S3 bucket for processed data
        self.output_bucket = ProcessedDataBucket(
            self,
            "OutputBucket"
        )

        # Custom Lambda function to process and chunk data
        self.lambda_function = CustomChunkingLambda(
            self,
            "ChunkingLambda",
            input_bucket_arn=self.input_bucket.bucket.bucket_arn,
            output_bucket_arn=self.output_bucket.bucket.bucket_arn
        )

        # Create the Data Source
        self.data_source = bedrock.CfnDataSource(
            self,
            "BedrockDataSource",
            name="GitHubDataSourceCustomChunking",
            knowledge_base_id=knowledge_base_id,
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.input_bucket.bucket.bucket_arn
                )
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="NONE"
                ),
                custom_transformation_configuration=bedrock.CfnDataSource.CustomTransformationConfigurationProperty(
                    intermediate_storage=bedrock.CfnDataSource.IntermediateStorageProperty(
                        s3_location=bedrock.CfnDataSource.S3LocationProperty(
                            uri=f"s3://{self.output_bucket.bucket.bucket_name}/"
                        )
                    ),
                    transformations=[
                        bedrock.CfnDataSource.TransformationProperty(
                            step_to_apply="POST_CHUNKING",
                            transformation_function=bedrock.CfnDataSource.TransformationFunctionProperty(
                                transformation_lambda_configuration=bedrock.CfnDataSource.TransformationLambdaConfigurationProperty(
                                    lambda_arn=self.lambda_function.lambda_function.function_arn
                                )
                            )
                        )
                    ]
                ),
            )
        )

        data_source_id = Fn.select(1, Fn.split("|", self.data_source.ref))

        self.data_scraper = DataScraper(
            self,
            "ScraperFunction",
            bucket_name=self.input_bucket.bucket.bucket_name,
            knowledge_base_id=knowledge_base_id,
            data_source_id=data_source_id 
        )       