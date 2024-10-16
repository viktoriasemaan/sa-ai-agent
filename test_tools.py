import tools

# TOOL 1

# query = "Tell me about my swissbox application - what's the architecture and components"
# response_ret = tools.answer_query_tool(query)
# print(response_ret)


# TOOL 2

# query = """
# Provide detailed configuration steps to build an analytics solution for my application using AWS services. 
# The architecture should encompass data ingestion, processing, and analytics, integrating several key AWS services.
# Here are the main components to consider:

# - **Amazon Kinesis Data Streams and AWS Lambda:** Set up to ingest and process real-time data streams from various application sources.
# - **Amazon S3:** Establish a durable and scalable data lake for storing raw ingested data, ensuring high availability and durability.
# - **AWS Glue:** Configure to automatically discover and catalog data stored in S3. Set up ETL jobs for transforming and loading data into Amazon Redshift for advanced analytics.
# - **Amazon Redshift:** Design a data warehouse for scalable and fast query performance, with appropriate configurations for cluster sizing, compression, partitioning, and performance tuning.
# - **Amazon Athena:** Enable querying of raw and transformed data directly in S3 using SQL, complementing data analysis performed in Redshift.
# - **Amazon QuickSight:** Develop visualizations and dashboards on top of data stored in Redshift or queried via Athena to gain actionable insights.
# - **AWS Step Functions:** Orchestrate the entire data processing workflow across these services, ensuring seamless operation and integration.

# """
# print(tools.iac_gen_tool(query))

# TOOL 3

query = "Estimate costs."
print(tools.iac_estimate_tool(query))
