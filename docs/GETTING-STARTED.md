# Getting Started with AWS Multi-Region E-commerce Platform

This guide explains the core stack implementation and how to incrementally add advanced features.

## Core Stack Architecture

The platform is built on three essential stacks that must be deployed in order:

1. **NetworkStack** - Creates VPC, subnets, and networking infrastructure
2. **CoreServicesStack** - Provisions DynamoDB tables and EventBridge event bus
3. **ApiComputeStack** - Deploys API Gateway and Lambda functions

These stacks form the foundation of your e-commerce backend and can operate independently of advanced features.

## Core Stack Implementation

### Stack Dependencies

```
PrimaryNetworkStack (VPC, subnets, NAT gateways)
        ↓
PrimaryCoreStack (DynamoDB tables, EventBridge)
        ↓
PrimaryApiStack (API Gateway, Lambda functions)
```

### Deployment Process

1. **Environment Setup**

   ```bash
   git clone git@github.com:Simodalstix/AWS-multiregion-ecommerce.git
   cd AWS-multiregion-ecommerce
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   npm install -g aws-cdk
   aws configure
   ```

2. **CDK Bootstrap** (required once per region)

   ```bash
   cdk bootstrap aws://YOUR-ACCOUNT-ID/ap-southeast-2
   ```

3. **Core Stack Deployment**
   ```bash
   cdk deploy PrimaryNetworkStack PrimaryCoreStack PrimaryApiStack --app "python app-stacks.py"
   ```

### Core Components Details

- **NetworkStack**: Creates a highly available VPC spanning 3 AZs with dual NAT gateways
- **CoreServicesStack**: Sets up DynamoDB Global Tables for multi-region data consistency
- **ApiComputeStack**: Exposes order processing APIs via API Gateway integrated with Lambda functions

## Advanced/Addon Stacks

After core deployment, you can incrementally add enterprise features:

### Security Stacks (Optional)

```bash
# Security baseline services (GuardDuty, Security Hub)
cdk deploy SecurityBaselineStack --app "python app-stacks.py"

# Centralized security logging
cdk deploy SecurityLakeStack --app "python app-stacks.py"

# SIEM integration (choose one)
cdk deploy SiemSinksStack -c sinkType=opensearch --app "python app-stacks.py"  # OpenSearch
cdk deploy SiemSinksStack -c sinkType=splunk --app "python app-stacks.py"     # Splunk
cdk deploy SiemSinksStack -c sinkType=elastic --app "python app-stacks.py"    # Elastic
```

### Multi-Region Disaster Recovery

```bash
# Deploy to secondary region for active-active configuration
cdk deploy SecondaryNetworkStack SecondaryCoreStack SecondaryApiStack --app "python app-stacks.py"
```

### CI/CD Pipeline

```bash
# Automated deployments on git push
aws secretsmanager create-secret --name github-token --secret-string "your-github-token"
cdk deploy PipelineStack
```

## Testing Core Deployment

### Verify Stack Status

```bash
aws cloudformation describe-stacks --stack-name PrimaryApiStack
```

### Test API Endpoints

```bash
# Get API endpoint URL
API_URL=$(aws cloudformation describe-stacks --stack-name PrimaryApiStack --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text)

# Create test order
curl -X POST ${API_URL}orders \
  -H "Content-Type: application/json" \
  -d '{"customerId": "test123", "items": [{"id": "item1", "quantity": 1, "price": 29.99}]}'
```

## Stack Dependencies Reference

All stack dependencies are explicitly defined in app-stacks.py:

- PrimaryCoreStack depends on PrimaryNetworkStack
- PrimaryApiStack depends on PrimaryCoreStack
- SecurityLakeStack depends on SecurityBaselineStack
- SiemSinksStack depends on SecurityLakeStack

## Troubleshooting

### Common Issues

1. **Missing AWS credentials**
   Ensure `aws configure` has been run with appropriate permissions

2. **CDK bootstrap required**
   Run `cdk bootstrap` in each region before deployment

3. **Stack dependency errors**
   Deploy stacks in the correct order as shown above

### Useful Commands

```bash
# List all available stacks
cdk list --app "python app-stacks.py"

# Preview changes before deployment
cdk diff PrimaryNetworkStack --app "python app-stacks.py"

# Check stack status
aws cloudformation describe-stacks --stack-name PrimaryNetworkStack
```

## Next Steps

1. Start with core stack deployment
2. Test API functionality
3. Add secondary region for disaster recovery
4. Implement CI/CD pipeline for automated deployments
5. Add security features as needed for compliance
