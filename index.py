import logging
from typing import Dict, Any
import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler to process API requests and route them to the appropriate tool functions.

    Args:
        event (Dict[str, Any]): The event data containing API request details.
        context (Any): The context object providing runtime information.

    Returns:
        Dict[str, Any]: The response dictionary containing the API response details.
    """
    logger.info("Received event: %s", event)

    action = event["actionGroup"]
    api_path = event["apiPath"]
    parameters = event["parameters"]
    input_text = event["inputText"]
    http_method = event["httpMethod"]

    logger.info("Input Text: %s", input_text)

    query = parameters[0]["value"]
    logger.info("Query: %s", query)

    response_code, body = process_api_request(api_path, query)

    response_body = {"application/json": {"body": str(body)}}
    logger.info("Response body: %s", response_body)

    action_response = {
        "actionGroup": action,
        "apiPath": api_path,
        "httpMethod": http_method,
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    return {"messageVersion": "1.0", "response": action_response}

def process_api_request(api_path: str, query: str) -> tuple[int, str]:
    """
    Process the API request based on the api_path.

    Args:
        api_path (str): The API path to determine which tool function to call.
        query (str): The query parameter for the tool function.

    Returns:
        tuple[int, str]: A tuple containing the response code and body.
    """
    api_handlers = {
        "/answer_query": tools.answer_query_tool,
        "/iac_gen": tools.iac_gen_tool,
        "/iac_estimate_tool": tools.iac_estimate_tool,
    }

    if api_path in api_handlers:
        return 200, api_handlers[api_path](query)
    else:
        return 400, f"{api_path} is not a valid API, try another one."

if __name__ == "__main__":
    # Example usage
    example_event = {
        "actionGroup": "exampleGroup",
        "apiPath": "/answer_query",
        "parameters": [{"value": "exampleQuery"}],
        "inputText": "exampleInput",
        "httpMethod": "GET"
    }
    example_context = {}

    response = handler(example_event, example_context)
    print(response)
