# Use a multi-stage build to extract the infracost binary
FROM infracost/infracost:ci-latest AS infracost

# Use the amazon/aws-lambda-python:3.11 as the base image
FROM amazon/aws-lambda-python:3.11

# Install tar, copy infracost, set up environment in a single layer
RUN yum install -y tar && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    mkdir /app && \
    yum -y remove tar

COPY --from=infracost /usr/bin/infracost /app/

ENV PATH="/app:${PATH}"

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python packages in a single layer
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -U boto3 botocore

# Copy function code
COPY index.py tools.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to the Lambda handler
CMD [ "index.handler" ]