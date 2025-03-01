import os
import json
import tempfile
import subprocess
from git import Repo
import boto3
from pprint import pprint
import requests

def verify_git_helpers():
    try:
        output = subprocess.check_output(["ls", "-l", "/opt/libexec/git-core"]).decode().strip()
        print("Git helpers in /opt/libexec/git-core:")
        print(output)
    except Exception as e:
        print("Error verifying git helpers:", e)

def detect_language(file_path: str) -> str:
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.html': 'html',
        '.css': 'css',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.sql': 'sql',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php'
    }
    ext = os.path.splitext(file_path)[1].lower()
    return LANGUAGE_MAP.get(ext, '')

def build_file_list(clone_dir: str):
    file_list = []
    for root, dirs, files in os.walk(clone_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), clone_dir)
            file_list.append(rel_path)
    return {"files": file_list}

def get_refined_prompt(file_list_json: str) -> str:
    base_prompt = (
        "You are a technical content curator. Your task is to help generate a markdown digest "
        "for a public repository that will be used in a retrieval-augmented generation (RAG) system. "
        "The repository may include source code, documentation, configuration files, tests, and other files. "
        "Analyze the following JSON representation of the repository's file list and select only those files "
        "that are essential for showcasing the project's core functionality, design, and public presentation. "
        "Exclude files used only for internal development such as build artifacts, tests, and configuration files.\n\n"
        "In addition exclude files that end with .svg, .ico or .css extensions. "
        "Return only a valid JSON object with a key 'include_files' that is a list of file paths to include, "
        "and a key 'include_dirs' that is a list of directory names to include. Do not include any additional commentary.\n\n"
        "Repository file list:\n"
    )
    return base_prompt + file_list_json

def call_llm_api(prompt: str):
    client = boto3.client('bedrock-runtime')
    model_id = "amazon.nova-pro-v1:0"
    message = {"role": "user", "content": [{"text": prompt}]}
    messages = [message]
    payload = {
        "modelId": model_id,
        "messages": messages
    }
    print("LLM Request Payload:")
    pprint(payload)
    try:
        response = client.converse(
            modelId=model_id,
            messages=messages
        )
        print("\nLLM Response:")
        pprint(response)
        return response
    except Exception as e:
        print("Error calling LLM API:", e)
        return None

def parse_llm_output(response) -> dict:
    try:
        output_message = response['output']['message']
        text = " ".join([item.get("text", "") for item in output_message["content"]])
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        decision = json.loads(text)
        return decision
    except Exception as e:
        print("Error parsing LLM output:", e)
        return {"include_files": ["README.md"], "include_dirs": []}

def process_pdf_file(file_path: str) -> str:
    client = boto3.client('bedrock-runtime')
    model_id = "amazon.nova-pro-v1:0"
    input_text = "Convert all text in this document to markdown."
    with open(file_path, "rb") as f:
        input_document = f.read()
    message = {
        "role": "user",
        "content": [
            {"text": input_text},
            {"document": {
                "name": "MyDocument",
                "format": "txt",
                "source": {"bytes": input_document}
            }}
        ]
    }
    messages = [message]
    try:
        response = client.converse(
            modelId=model_id,
            messages=messages
        )
        output_message = response['output']['message']
        text = " ".join([item.get("text", "") for item in output_message["content"]])
        return text
    except Exception as e:
        print(f"Error processing PDF file {file_path}: {e}")
        return "Error processing PDF file."

def format_file_content(file_path: str, content: str) -> str:
    lang = detect_language(file_path)
    escaped_content = content.replace("```", "'''")
    return f"## File: {file_path}\n\n```{lang}\n{escaped_content}\n```\n"

def generate_documentation(file_path: str, file_content: str, prompt_template: str) -> str:
    # Build a prompt using the placeholder prompt template.
    prompt = prompt_template.format(file_path=file_path, content=file_content)
    print(f"Generating documentation for {file_path} with prompt: {prompt[:100]}...")
    response = call_llm_api(prompt)
    try:
        output_message = response['output']['message']
        doc_text = " ".join([item.get("text", "") for item in output_message["content"]])
        return doc_text.strip() + "\n\n"  # Append spacing after the header.
    except Exception as e:
        print(f"Error generating documentation for {file_path}: {e}")
        return ""

def get_public_repos(username: str):
    url = f"https://api.github.com/users/{username}/repos"
    try:
        response = requests.get(url)
        response.raise_for_status()
        repos = response.json()
        # Return a list of tuples: (clone_url, repository_name)
        return [(repo['clone_url'], repo['name']) for repo in repos]
    except Exception as e:
        print("Error retrieving public repos for user", username, ":", e)
        return []

def lambda_handler(event, context):
    # Verify git helper installation
    verify_git_helpers()
    try:
        exec_path = subprocess.check_output(["git", "--exec-path"]).decode().strip()
        print("Git exec path:", exec_path)
    except Exception as e:
        print("Error running git --exec-path:", e)
        
    # Retrieve required environment variables
    github_user = os.environ.get("GITHUB_USER")
    bucket_name = os.environ.get("BUCKET_NAME")
    
    if not github_user or not bucket_name:
        print("Environment variables GITHUB_USER or BUCKET_NAME not set.")
        return {"status": "error", "message": "Missing environment variables."}
    
    s3_client = boto3.client('s3')
    repos = get_public_repos(github_user)
    
    if not repos:
        print("No public repositories found for user:", github_user)
        return {"status": "error", "message": f"No public repositories found for user {github_user}"}
    
    # Process each repository one at a time
    for repo_url, repo_name in repos:
        print(f"\nProcessing repository: {repo_name} ({repo_url})")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                Repo.clone_from(repo_url, temp_dir)
            except Exception as e:
                print("Error cloning repository:", e)
                continue

            file_tree = build_file_list(temp_dir)
            file_tree_json = json.dumps(file_tree, indent=2)
            prompt = get_refined_prompt(file_tree_json)
            response = call_llm_api(prompt)
            decision = parse_llm_output(response)

            # Use only the explicit file list from the LLM output
            selected_files = set(decision.get("include_files", []))
            
            for file_path in sorted(selected_files):
                abs_path = os.path.join(temp_dir, file_path)
                if os.path.isfile(abs_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext == ".pdf":
                        md_text = process_pdf_file(abs_path)
                        markdown_content = f"## File: {file_path}\n\n{md_text}\n"
                    else:
                        try:
                            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                                file_content = f.read()
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")
                            continue

                        documentation_header = ""
                        # Only generate documentation for code files (exclude markdown and PDFs)
                        if ext not in [".md", ".pdf"]:
                            placeholder_prompt = (
                                """
                                Below is a code file named {file_path} from a project that powers a website with a chatbot and a blog. The chatbot is connected to an AWS CDK-based backend that provisions all necessary infrastructure.
                                Your task is to generate a concise, structured, and well-formatted markdown documentation header for this file. The documentation should:
                                -Summarize the file’s purpose and its role in the project.
                                -Explain how it interacts with other components, such as the chatbot, blog, CDK infrastructure, APIs, or external services.
                                -Describe its usage and importance within the system.
                                -List any dependencies, setup instructions, or key considerations if applicable.
                                Ensure the output is clear, professional, and formatted in markdown syntax for easy readability.
                                Code to document:\n\n{content}\n\nGenerated Documentation:
                                """
                            )
                            documentation_header = generate_documentation(file_path, file_content, placeholder_prompt)
                        file_markdown = format_file_content(file_path, file_content)
                        markdown_content = documentation_header + file_markdown
                    
                    # Create an S3 key for the markdown file
                    s3_key = f"markdown_digest/{repo_name}/{file_path}.md"
                    try:
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=s3_key,
                            Body=markdown_content,
                            ContentType='text/markdown'
                        )
                        print(f"Uploaded markdown to s3://{bucket_name}/{s3_key}")
                    except Exception as e:
                        print(f"Error uploading {file_path} to S3: {e}")

    knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
    data_source_id = os.environ.get("DATA_SOURCE_ID")
    
    if not knowledge_base_id or not data_source_id:
        print("Environment variables KNOWLEDGE_BASE_ID or DATA_SOURCE_ID not set.")
        return {"status": "error", "message": "Missing knowledge base or data source ID."}

    # Instantiate the Bedrock agent client and call start_ingestion_job
    bedrock_client = boto3.client('bedrock-agent')
    try:
        ingestion_response = bedrock_client.start_ingestion_job(
            dataSourceId=data_source_id,
            knowledgeBaseId=knowledge_base_id,
            description="Triggered by Lambda after data ingestion"
        )
        print("Ingestion job started:", ingestion_response)
    except Exception as e:
        print("Error starting ingestion job:", e)

    return {"status": "success", "message": "Processing complete."}
