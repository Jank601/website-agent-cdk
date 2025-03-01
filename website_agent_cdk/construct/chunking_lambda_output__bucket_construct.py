from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct

class ProcessedDataBucket(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.bucket = s3.Bucket(
            self,
            "LambdaOutputBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )