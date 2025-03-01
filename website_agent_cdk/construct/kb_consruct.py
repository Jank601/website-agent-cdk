import json
import os
from aws_cdk import (
    aws_bedrock as bedrock,
    aws_iam as iam,
    Stack,
)
from constructs import Construct
from website_agent_cdk.construct.pincone_secret_construct import PineconeSecretConstruct
from website_agent_cdk.construct.data_source_construct import DataSourceConstruct

class KnowledgeBaseConstruct(Construct):
    def __init__(self, scope: Construct, id: str,):
        super().__init__(scope, id)

        # Load configuration from config.json
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config.json")
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
                pinecone_endpoint = config.get("pineconeEndpoint")
                if not pinecone_endpoint:
                    raise ValueError("pineconeEndpoint not found in the config.json file")
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_file}")
        except json.JSONDecodeError:
            raise ValueError(f"Config file is not a valid JSON file: {config_file}")

        # Configuration for the embedding model and Pinecone
        embedding_model_id = "amazon.titan-embed-text-v1"
        pinecone_namespace = "default"

        # Create Pinecone secret
        pinecone_secret = PineconeSecretConstruct(
            self,
            "PineconeSecretConstruct",
            secret_name="pinecone-api-secret",
        )

        # Create IAM Role for Knowledge Base
        kb_role = iam.Role(
            self,
            "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="IAM role for the Bedrock Knowledge Base",
            # Add inline policy directly during role creation
            inline_policies={
                "SecretsAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue",
                                "secretsmanager:DescribeSecret"
                            ],
                            resources=[pinecone_secret.secret_arn]
                        )
                    ]
                )
            }
        )

        # Add Bedrock permissions
        kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob",
                ],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/*",
                    f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/{embedding_model_id}"
                ]
            )
        )

        # Add S3 permissions
        kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                ],
                resources=[
                    f"arn:aws:s3:::{Stack.of(self).stack_name.lower()}-*",
                    f"arn:aws:s3:::{Stack.of(self).stack_name.lower()}-*/*"
                ]
            )
        )

        # Add Lambda invoke permissions
        kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[
                    f"arn:aws:lambda:{Stack.of(self).region}:{Stack.of(self).account}:function:{Stack.of(self).stack_name}*"
                ]
            )
        )

        # Create the Bedrock Knowledge Base with Pinecone storage
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "PSCKnowledgeBase",
            name="PSCKnowledgeBase",
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/{embedding_model_id}",
                )
            )
        ,
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="PINECONE",
                pinecone_configuration=bedrock.CfnKnowledgeBase.PineconeConfigurationProperty(
                    connection_string=pinecone_endpoint,
                    credentials_secret_arn=pinecone_secret.secret_arn,
                    namespace=pinecone_namespace,
                    field_mapping=bedrock.CfnKnowledgeBase.PineconeFieldMappingProperty(
                        metadata_field="metadata",
                        text_field="text",
                    )
                )
            )
        )

        # Create the Data Source using the separate DataSourceConstruct
        self.data_source = DataSourceConstruct(
            self,
            "KnowledgeBaseDataSource",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id
        )

        # Ensure the Data Source is created after the Knowledge Base
        self.data_source.node.add_dependency(self.knowledge_base)