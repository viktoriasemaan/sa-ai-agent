import tools_new

# Test Tool 1 - Knowledge Base 
query = "I want to build an ecommerce website on AWS. What should I do?"
# response_ret = tools_new.retrieve_and_generate_response(query)
# tools_new.response_print(response_ret)
response_text = tools_new.retrieve_and_generate_response(query)
print(response_text)