# Contract Event Mismatch Checker (AWS Lambda + Docker)

This project checks for mismatches between Salesforce contract events and data in a Redshift-based analytics warehouse. It uses a serverless architecture powered by AWS Lambda with a Docker container image.

## What It Does

- Connects to Salesforce using SOQL via the REST API  
- Connects to Redshift (or PostgreSQL) to query warehouse records  
- Compares `LastModifiedDate` in Salesforce vs `lastupdatedatetime` in the warehouse  
- Outputs mismatched records to an S3 bucket as a `.csv` report  

## Stack

- Python 3.11 
- Docker  
- AWS Lambda (Container Image)  
- Redshift / PostgreSQL (via psycopg2)  
- Salesforce API (via simple-salesforce)  
- Amazon S3  

## Project Structure

contract-check-lambda/
├── app.py               # Lambda function logic
├── Dockerfile           # Lambda image definition
├── requirements.txt     # Python dependencies
├── .env.example         # Sample environment variables
└── README.md            # Project documentation

## Deployment Steps

### Prerequisites

- AWS CLI and Docker installed  
- S3 bucket created for output  
- Redshift (or Postgres) DB accessible from Lambda  
- Salesforce credentials with API access  

### 1. Build and Push Docker Image

```bash
docker build -t contract-check .

docker tag contract-check:latest [account_id].dkr.ecr.[region].amazonaws.com/contract-check:latest

docker push [account_id].dkr.ecr.[region].amazonaws.com/contract-check:latest
```

### 2. Create Lambda Function from Image

- Go to AWS Lambda → Create Function → Container image  
- Select the ECR image you just pushed  
- Set environment variables (see .env.example)  
- Configure timeout, memory, and VPC access if needed for Redshift

### 3. Schedule or Trigger

- Use Amazon EventBridge (CloudWatch) to run on a schedule  
- Or manually trigger via the Lambda console  

## Output

The function uploads the mismatch report to:

`s3://<your-bucket-name>/contract_event_mismatches.csv`

## Local Testing

To run locally:

1. Copy .env.example → .env  
2. Set your credentials and values  
3. Run the script with:

``` bash
export $(cat .env | xargs)
python app.py
```

## Environment Variables

See .env.example for structure.