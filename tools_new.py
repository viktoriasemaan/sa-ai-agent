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
