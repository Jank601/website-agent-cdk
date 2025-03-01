import json
from abc import abstractmethod, ABC
from typing import List
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Abstract base class for chunking logic
class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        raise NotImplementedError()

# NoChunker returns the entire text as one chunk
class NoChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        return [text]

def lambda_handler(event, context):
    logger.debug("input={}".format(json.dumps(event)))
    s3 = boto3.client('s3')

    # Extract required parameters from the event
    input_files = event.get("inputFiles")
    input_bucket = event.get("bucketName")

    if not all([input_files, input_bucket]):
        raise ValueError("Missing required input parameters")

    output_files = []
    # Use NoChunker so that each file is treated as a single chunk
    chunker = NoChunker()

    for input_file in input_files:
        content_batches = input_file.get("contentBatches", [])
        file_metadata = input_file.get("fileMetadata", {})
        original_file_location = input_file.get("originalFileLocation", {})

        processed_batches = []
        for batch in content_batches:
            input_key = batch.get("key")
            if not input_key:
                raise ValueError("Missing key in content batch")

            # Read file content from S3
            file_content = read_s3_file(s3, input_bucket, input_key)

            # Process content using our custom chunker (merging into one chunk)
            chunked_content = process_content(file_content, chunker)

            # Build an output key that mirrors the input key within an "Output/" prefix
            output_key = f"Output/{input_key}"

            # Write the chunked content back to S3
            write_to_s3(s3, input_bucket, output_key, chunked_content)

            processed_batches.append({
                "key": output_key
            })

        output_file = {
            "originalFileLocation": original_file_location,
            "fileMetadata": file_metadata,
            "contentBatches": processed_batches
        }
        output_files.append(output_file)

    return {"outputFiles": output_files}

def read_s3_file(s3_client, bucket, key):
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))

def write_to_s3(s3_client, bucket, key, content):
    s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(content))

def process_content(file_content: dict, chunker: Chunker) -> dict:
    """
    Merges all parts of a file's content into a single chunk.
    If the file has a 'fileContents' array, all 'contentBody' values are joined;
    otherwise, the entire file content is converted to a string.
    """
    # If fileContents exists, merge all contentBody values into one string.
    if "fileContents" in file_content:
        combined_text = "\n".join(item.get("contentBody", "") for item in file_content["fileContents"])
    else:
        combined_text = str(file_content)
    
    # Use the provided chunker (NoChunker returns one chunk)
    chunks = chunker.chunk(combined_text)

    # Prepare the output in the expected JSON format
    return {
        "fileContents": [{
            "contentBody": chunk,
            "contentType": "TEXT",
            "contentMetadata": {}
        } for chunk in chunks]
    }
