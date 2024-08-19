import json
import os
import subprocess
import boto3
from datetime import datetime

# Define the knowledge base ID
kb_id = "OUYPGZVGKR"
region_name = "us-west-2"

# Initialize Bedrock runtime clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=region_name)
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name)

# Function to retrieve and generate response
def answer_query_tool(query):
    response_ret = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id, 
        nextToken='string',
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults":5,
            } 
        },
        retrievalQuery={'text': query}
    )

    foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

    response = bedrock_agent_runtime_client.retrieve_and_generate(
        input={
            "text": query
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                'knowledgeBaseId': kb_id,
                "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region_name, foundation_model),
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults":5
                    } 
                }
            }
        }
    )

#    print(response['output']['text'], end='\n'*2)
#    return response_ret
    return response['output']['text']

def response_print(retrieve_resp):
    # Structure 'retrievalResults': list of contents. Each list has content, location, score, metadata
    for num, chunk in enumerate(retrieve_resp['retrievalResults'], 1):
        print(f'Chunk {num}: ', chunk['content']['text'], end='\n'*2)
        print(f'Chunk {num} Location: ', chunk['location'], end='\n'*2)
        print(f'Chunk {num} Score: ', chunk['score'], end='\n'*2)
        print(f'Chunk {num} Metadata: ', chunk['metadata'], end='\n'*2)



# Additional function for IaC generation using Bedrock Converse API
def iac_gen_tool(prompt):
    """
    Generates Infrastructure as Code (IaC) scripts based on a customer's request.

    Args:
        prompt (str): The customer's request.

    Returns:
        str: The S3 path where the generated IaC code is saved.
    """
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    # Define the conversation prompt
    prompt_ending = """Assume the role of a DevOps Engineer. Thoroughly analyze the provided customer requirements to determine all necessary AWS services and their integrations for the solution.
            Generate the Terraform code required to provision and configure each AWS service, writing the code step-by-step. Ensure the code adheres to best practices and is valid Terraform syntax. Provide only the final Terraform code, without any additional comments, explanations, markdown formatting, or special symbols. 
            Requirements:"""

    messages = [
        {
            "role": "user",
            "content": [
                {"text": prompt_ending + "\n" + prompt}
            ]
        }
    ]
    
    response = client.converse(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        messages=messages
    )

    generated_text = response['output']['message']['content'][0]['text']
    
    # Save to S3
    s3 = boto3.client('s3')
    bucket_name = "bedrock-agent-generate-iac-estimate-cost"
    prefix = "iac-code/"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"iac_{timestamp}.tf"
    s3_path = f"{prefix}{filename}"
    
    # Write the Terraform code to a BytesIO object and upload it to S3
    from io import BytesIO
    file_buffer = BytesIO(generated_text.encode('utf-8'))
    s3.upload_fileobj(file_buffer, bucket_name, s3_path)
    
    return f"File saved to S3 bucket {bucket_name} at {s3_path}"



def iac_estimate_tool(prompt):
    """
    Estimates the cost of an AWS infrastructure using Infracost.

    Args:
        prompt (str): The customer's request.

    Returns:
        str: The cost estimation.
    """
    # Get terraform code from S3
    s3 = boto3.client('s3')
    bucket_name = "bedrock-agent-generate-iac-estimate-cost"
    prefix_code = "iac-code"
    prefix_cost = "iac-cost"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_dir = '/tmp/infracost-evaluate'
    
    # Create the local directory if it doesn't exist
    os.makedirs(local_dir, exist_ok=True)

    # List objects in the S3 folder sorted by LastModified in descending order
    objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix_code)
    sorted_objects = sorted(objects['Contents'], key=lambda obj: obj['LastModified'], reverse=True)
    
    # Get the latest file key
    latest_file_key = sorted_objects[0]['Key']
    
    # Download the latest file
    local_file_path = os.path.join(local_dir, os.path.basename(latest_file_key))
    s3.download_file(bucket_name, latest_file_key, local_file_path)
    
    # Generate timestamp-based file name
    cost_filename = f"cost-evaluation-{timestamp}.txt"
    cost_file_path = f"/tmp/{cost_filename}"
    
    # Run Infracost CLI command
    infracost_cmd = f"infracost breakdown --path /tmp/infracost-evaluate > {cost_file_path}"
    try:
        subprocess.run(infracost_cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        # Read the result file even if the command returns a non-zero exit code
        with open(cost_file_path, 'r') as f:
            cost_file = f.read()
        print(f"Infracost command returned non-zero exit code: {e.returncode}")
        print(f"Result: {cost_file}")
    else:
        with open(cost_file_path, 'r') as f:
            cost_file = f.read()
        print(f"Result: {cost_file}")
    
    # Upload cost evaluation file to S3 under the "iac-cost" folder
    s3_cost_result = os.path.join(prefix_cost, cost_filename)
    s3.upload_file(cost_file_path, bucket_name, s3_cost_result)



    # Call Amazon Bedrock Converse API instead of the old invoke model API
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    system_prompt = """Given the estimated costs for an AWS cloud infrastructure, provide a breakdown of the monthly cost for each service. 
                    For services with multiple line items (e.g., RDS), aggregate the costs into a single total for that service. 
                    Present the cost analysis as a list, with each service and its corresponding monthly cost. Ignore the path to Terraform code; you already have all the required information.
                    Finally, include the total monthly cost for the entire infrastructure."""
    messages = [
        {
            "role": "user",
            "content": [
                {"text": cost_file + "\n"  + prompt  + "\n" + system_prompt}
            ]
        }
    ]
    
    response = client.converse(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        messages=messages
    )

    generated_text = response['output']['message']['content'][0]['text']
 
    return generated_text
