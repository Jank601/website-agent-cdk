import json
import os
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class PineconeSecretConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, secret_name: str):
        super().__init__(scope, construct_id)

        # Define the path to the config.json file in the project root
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config.json")

        # Load the API key from the JSON file
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
                secret_value = config.get("pineconeApiKey")
                if not secret_value:
                    raise ValueError("pineconeApiKey not found in the config.json file")
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_file}")
        except json.JSONDecodeError:
            raise ValueError(f"Config file is not a valid JSON file: {config_file}")

        # Create the Secrets Manager secret
        self.secret = secretsmanager.CfnSecret(
            self,
            "PineconeSecret",
            name=secret_name,
            description="Secret for storing Pinecone API key",
            secret_string=json.dumps({"apiKey": secret_value})  # Using json.dumps for proper JSON formatting
        )

        # Access the ARN of the created secret
        self.secret_arn = self.secret.ref