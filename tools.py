import json
import os
from datetime import datetime
from typing import Dict, Any
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from environment variables or a config file
KB_ID = os.getenv('KB_ID', 'OUYPGZVGKR')
REGION_NAME = os.getenv('AWS_REGION', 'us-west-2')
FOUNDATION_MODEL = os.getenv('FOUNDATION_MODEL', 'anthropic.claude-3-sonnet-20240229-v1:0')
BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'bedrock-agent-generate-iac-estimate-cost')

# Initialize Bedrock runtime clients
try:
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION_NAME)
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION_NAME)
    s3_client = boto3.client('s3')
except BotoCoreError as e:
    logger.error(f"Failed to initialize AWS clients: {e}")
    raise

def answer_query_tool(query: str) -> str:
    """
    Retrieve data from RAG and generate a response.

    Args:
        query (str): The user's query.

    Returns:
        str: The generated response.
    """
    try:
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KB_ID,
                    'modelArn': f"arn:aws:bedrock:{REGION_NAME}::foundation-model/{FOUNDATION_MODEL}",
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 5
                        } 
                    }
                }
            }
        )
        return response['output']['text']
    except ClientError as e:
        logger.error(f"Error in answer_query_tool: {e}")
        return f"An error occurred: {str(e)}"

def iac_gen_tool(prompt: str) -> str:
    """
    Generate Infrastructure as Code (IaC) scripts based on a customer's request.

    Args:
        prompt (str): The customer's request.

    Returns:
        str: The S3 path where the generated IaC code is saved.
    """
    try:
        iac_system_prompt = """
You are a skilled DevOps Engineer tasked with creating a comprehensive AWS infrastructure using Terraform. Your mission is to:

1. Analyze the following customer requirements in detail.

2. Identify all necessary AWS services to fulfill these requirements, considering:
   - Core infrastructure components
   - Security and networking needs
   - Data storage and management solutions
   - Application hosting and scaling requirements
   - Monitoring and logging services

3. Determine the optimal integrations between these AWS services to create a cohesive solution.

4. Generate Terraform code to provision and configure each identified AWS service:
   - Write the code incrementally, service by service
   - Use the latest Terraform syntax and AWS provider version
   - Implement best practices for resource naming, tagging, and organization
   - Ensure proper dependencies and connections between resources

5. Your Terraform code should:
   - Be complete and ready for execution
   - Use variables for customizable values
   - Implement proper data types and validation where applicable
   - Include necessary providers and backend configuration

6. Output format:
   - Provide only the final, complete Terraform code
   - Do not include comments, explanations, markdown formatting, or special symbols
   - Ensure the code is properly indented and formatted for readability

7. Verify that your code:
   - Is valid Terraform syntax
   - Covers all requirements specified by the customer
   - Follows AWS and Terraform best practices for security and efficiency

Now, please analyze these customer requirements and generate the appropriate Terraform code:
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"text": f"{iac_system_prompt}\n\nCustomer Requirements:\n{prompt}"}
                ]
            }
        ]
        
        response = bedrock_runtime.converse(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            messages=messages
        )

        generated_text = response['output']['message']['content'][0]['text']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"iac_{timestamp}.tf"
        s3_path = f"iac-code/{filename}"
        
        file_buffer = BytesIO(generated_text.encode('utf-8'))
        s3_client.upload_fileobj(file_buffer, BUCKET_NAME, s3_path)
        
        return f"File saved to S3 bucket {BUCKET_NAME} at {s3_path}"
    except ClientError as e:
        logger.error(f"Error in iac_gen_tool: {e}")
        return f"An error occurred: {str(e)}"

def iac_estimate_tool(prompt: str) -> str:
    """
    Estimate the cost of an AWS infrastructure using Infracost.

    Args:
        prompt (str): The customer's request.

    Returns:
        str: The cost estimation.
    """
    try:
        # Get the latest Terraform file from S3
        objects = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='iac-code')
        sorted_objects = sorted(objects['Contents'], key=lambda obj: obj['LastModified'], reverse=True)
        latest_file_key = sorted_objects[0]['Key']
        
        # Download the latest file
        local_dir = '/tmp/infracost-evaluate'
        os.makedirs(local_dir, exist_ok=True)
        local_file_path = os.path.join(local_dir, os.path.basename(latest_file_key))
        s3_client.download_file(BUCKET_NAME, latest_file_key, local_file_path)
        
        # Run Infracost CLI command
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cost_filename = f"cost-evaluation-{timestamp}.txt"
        cost_file_path = f"/tmp/{cost_filename}"
        
        os.system(f"infracost breakdown --path {local_file_path} > {cost_file_path}")
        
        with open(cost_file_path, 'r') as f:
            cost_file = f.read()
        
        # Upload cost evaluation file to S3
        s3_cost_result = f"iac-cost/{cost_filename}"
        s3_client.upload_file(cost_file_path, BUCKET_NAME, s3_cost_result)

        # Generate cost analysis using Bedrock
        system_prompt = """You are a specialized AI assistant focused on AWS cloud cost analysis. Your primary function is to analyze estimated costs for AWS cloud infrastructure and provide clear, accurate breakdowns. Follow these guidelines:

1. Input: You will receive estimated costs for various AWS services. This is not raw infrastructure data, but pre-calculated cost estimates.

2. Output Format:
   - Present a list of AWS services with their aggregated monthly costs.
   - For services with multiple line items (e.g., RDS), combine them into a single total for that service.
   - Conclude with the total monthly cost for the entire infrastructure.

3. Calculation Rules:
   - Aggregate costs for services with multiple components.
   - Double-check all mathematical calculations for accuracy.
   - Ensure the sum of individual service costs matches the reported total cost.

4. Presentation:
   - List each service followed by its monthly cost.
   - Use clear, concise language.
   - Round costs to two decimal places.

5. Additional Notes:
   - Ignore any references to Terraform code paths or raw infrastructure details.
   - If there are discrepancies or unclear data, highlight them in your response.

6. Example Output Structure:
   Service 1: $XX.XX
   Service 2: $YY.YY
   ...
   Total Monthly Cost: $ZZZ.ZZ

Remember, your goal is to provide a clear, accurate, and easily understandable breakdown of AWS infrastructure costs.
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"text": f"{cost_file}\n{prompt}\n{system_prompt}"}
                ]
            }
        ]
        
        response = bedrock_runtime.converse(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            messages=messages
        )

        return response['output']['message']['content'][0]['text']
    except ClientError as e:
        logger.error(f"Error in iac_estimate_tool: {e}")
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":
    # Example usage
    query_result = answer_query_tool("What is Amazon S3?")
    print(query_result)

    iac_result = iac_gen_tool("Create an EC2 instance with an S3 bucket")
    print(iac_result)

    estimate_result = iac_estimate_tool("Estimate the cost of the infrastructure")
    print(estimate_result)