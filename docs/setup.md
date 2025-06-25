# Setup Guide

This guide walks you through setting up and deploying the multi-region e-commerce platform.

## Prerequisites

1. **AWS Account and CLI**

   - An AWS account with appropriate permissions
   - AWS CLI installed and configured
   - Default region set to ap-southeast-2 (Sydney)

2. **Development Tools**

   - Python 3.9 or later
   - Node.js 16 or later (for CDK CLI)
   - Git

3. **GitHub Setup**
   - A GitHub account
   - Personal access token with `repo` and `admin:repo_hook` permissions
   - Token stored in AWS Secrets Manager as 'github-token'

## Installation

1. **Clone the Repository**

   ```bash
   git clone git@github.com:Simodalstix/AWS-multiregion-ecommerce.git
   cd AWS-multiregion-ecommerce
   ```

2. **Create Python Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   npm install -g aws-cdk
   ```

## Configuration

1. **AWS Credentials**
   Ensure your AWS credentials are configured with appropriate permissions:

   ```bash
   aws configure
   ```

2. **GitHub Token**
   Store your GitHub personal access token in AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
       --name github-token \
       --secret-string "your-github-token"
   ```

## Deployment

1. **Bootstrap CDK (First time only)**
   Run in both primary (ap-southeast-2) and secondary (us-west-2) regions:

   ```bash
   cdk bootstrap aws://ACCOUNT-NUMBER/ap-southeast-2
   cdk bootstrap aws://ACCOUNT-NUMBER/us-west-2
   ```

2. **Deploy the Pipeline Stack**

   ```bash
   cdk deploy PipelineStack
   ```

   This will create the CI/CD pipeline that handles deployment of all other stacks.

3. **Initial Pipeline Run**
   The pipeline will automatically start deploying the infrastructure stacks in both regions:
   - Network infrastructure
   - Core services (DynamoDB, EventBridge)
   - API and compute resources

## Verification

1. **Check Stack Status**

   ```bash
   cdk ls          # List all stacks
   cdk diff        # Check for pending changes
   ```

2. **Test API Endpoints**
   After deployment completes, you can test the API endpoints:

   ```bash
   # Create an order
   curl -X POST https://[API-GATEWAY-URL]/prod/orders \
       -H "Content-Type: application/json" \
       -d '{"customerId": "123", "items": [{"id": "item1", "quantity": 1, "price": 29.99}]}'

   # Get an order
   curl https://[API-GATEWAY-URL]/prod/orders/[ORDER-ID]
   ```

## Monitoring

1. **CloudWatch Dashboards**

   - Navigate to CloudWatch in both regions to view metrics
   - Check API Gateway, Lambda, and DynamoDB metrics

2. **Pipeline Status**
   - Monitor deployment progress in CodePipeline console
   - Check CodeBuild logs for detailed build information

## Cleanup

To avoid incurring charges, you can remove all resources:

```bash
cdk destroy --all
```

## Troubleshooting

1. **Pipeline Failures**

   - Check CodeBuild logs for build errors
   - Verify GitHub webhook configuration
   - Ensure GitHub token is valid

2. **API Issues**

   - Check API Gateway CloudWatch logs
   - Verify Lambda function logs
   - Check DynamoDB capacity and throttling metrics

3. **Common Problems**
   - Missing GitHub token in Secrets Manager
   - Insufficient IAM permissions
   - Region configuration mismatches

## Support

For issues and feature requests, please create an issue in the GitHub repository.
