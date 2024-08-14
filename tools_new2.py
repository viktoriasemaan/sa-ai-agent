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
def retrieve_and_generate_response(query):
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
def iac_gen_converse_tool(prompt):
    """
    Generates Infrastructure as Code (IaC) scripts using the Amazon Bedrock Converse API.

    Args:
        prompt (str): The customer's request.

    Returns:
        str: The S3 path where the generated IaC code is saved.
    """
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    # Define the conversation prompt
    messages = [
        {
            "role": "user",
            "content": [
                {"text": prompt}
            ]
        }
    ]
    
    response = client.converse(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
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
