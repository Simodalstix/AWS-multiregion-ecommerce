# Serverless Multi-Region E-commerce Platform with Security and Monitoring

![Architecture Overview](screenshots/AWS-multiregion-ecommerce.png)

## Overview

This project is a **serverless, event-driven e-commerce platform** built on AWS with **multi-region high availability** and **disaster recovery** capabilities. The architecture provides automatic failover between AWS regions (Australia and US West) and includes comprehensive enterprise security and monitoring features, including SIEM integration and compliance capabilities.

### Core Features

- **Serverless Architecture**: No servers to manage, auto-scaling infrastructure
- **Multi-Region Deployment**: Active-active configuration across AWS regions
- **Event-Driven Design**: Loose coupling between services via EventBridge
- **Disaster Recovery**: Automatic failover capabilities (manual activation currently, with plans for enhanced automation)
- **CI/CD Pipeline**: Automated deployments via CodePipeline and CodeBuild

### Additional Enterprise Features

The platform includes optional stacks for enterprise requirements:

- **Security Monitoring**: GuardDuty, Security Hub, and Detective integration
- **Centralized Logging**: Security Lake with OCSF normalization
- **SIEM Integration**: Connect to OpenSearch, Splunk, or Elastic for security analytics
- **Compliance**: AWS Config rules and conformance packs

## Getting Started

For detailed deployment instructions, see [Getting Started Guide](docs/GETTING-STARTED.md).

Quick deployment of core infrastructure:

```bash
# Setup environment
git clone git@github.com:Simodalstix/AWS-multiregion-ecommerce.git
cd AWS-multiregion-ecommerce
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g aws-cdk
aws configure

# Bootstrap CDK (one-time setup)
cdk bootstrap aws://YOUR-ACCOUNT-ID/ap-southeast-2

# Deploy core infrastructure
cdk deploy PrimaryNetworkStack PrimaryCoreStack PrimaryApiStack --app "python app-stacks.py"

# Test your API
API_URL=$(aws cloudformation describe-stacks --stack-name PrimaryApiStack --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text)
echo "API Endpoint: $API_URL"

curl -X POST ${API_URL}orders \
  -H "Content-Type: application/json" \
  -d '{"customerId": "123", "items": [{"id": "item1", "quantity": 1, "price": 29.99}]}'
```

## 🎯 What This Actually Does

This project gives you a **production-ready e-commerce backend** with:

- ✅ **Multi-region high availability** (Australia + US West)
- ✅ **Serverless architecture** (no servers to manage)
- ✅ **Auto-scaling** (handles any traffic volume)
- ✅ **Disaster recovery** (automatic failover with manual activation currently)
- ✅ **Event-driven design** (extensible for new features)
- ✅ **Security and monitoring** (comprehensive enterprise features including SIEM integration)

## 📁 Project Structure - What Matters

```
├── app-stacks.py              # 🎯 START HERE - Deploy this first
├── infrastructure/lib/
│   ├── network_stack.py       # VPC, subnets (required)
│   ├── core_services_stack.py # DynamoDB tables (required)
│   ├── api_compute_stack.py   # API Gateway + Lambda (required)
│   ├── pipeline_stack.py      # CI/CD (optional - for automation)
│   └── security/              # Enterprise security (optional)
├── src/functions/             # Your actual business logic
└── docs/                      # Documentation (this file!)
```

## 🎯 Deployment Options - Pick Your Path

### Option 1: Manual Deployment (Recommended for Learning)

Deploy stacks directly using CDK:

```bash
# Deploy core infrastructure only (ignore security for now)
cdk deploy PrimaryNetworkStack PrimaryCoreStack PrimaryApiStack --app "python app-stacks.py"

# Later, add secondary region for disaster recovery
cdk deploy SecondaryNetworkStack SecondaryCoreStack SecondaryApiStack --app "python app-stacks.py"
```

### Option 2: CI/CD Pipeline (For Production)

Automatically deploy on git push:

```bash
# 1. Store GitHub token in AWS Secrets Manager
aws secretsmanager create-secret --name github-token --secret-string "your-github-token"

# 2. Deploy pipeline
cdk deploy PipelineStack

# 3. Now any git push to main automatically deploys!
```

## 🔧 Testing Your Deployment

### Unit Tests

```bash
python -m pytest tests/ -v
```

### API Testing

```bash
# Get your API endpoint
aws cloudformation describe-stacks --stack-name PrimaryApiStack --query 'Stacks[0].Outputs'

# Test creating an order
curl -X POST https://YOUR-API-URL/prod/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId": "123", "items": [{"id": "item1", "quantity": 1, "price": 29.99}]}'

# Test getting an order
curl https://YOUR-API-URL/prod/orders/YOUR-ORDER-ID
```

## 🛡️ Security Features (Advanced)

The security components are **completely optional** enterprise features:

- **Security Lake**: Centralized security logging
- **SIEM Integration**: Connect to Splunk, Elastic, or OpenSearch
- **GuardDuty**: Threat detection
- **Security Hub**: Security compliance monitoring

**Skip these initially!** Focus on getting the core e-commerce system working first.

See [SECURITY-LAKE.md](docs/SECURITY-LAKE.md) for security documentation (but only after core system works).

## 📚 Detailed Documentation

- [Setup Guide](docs/setup.md) - Complete setup instructions
- [Architecture](docs/architecture.md) - Technical architecture details
- [Security Lake](docs/SECURITY-LAKE.md) - Security and SIEM integration

## 🎯 Key Files You Should Know

| File                                                          | Purpose                     | When to Use                          |
| ------------------------------------------------------------- | --------------------------- | ------------------------------------ |
| [`app-stacks.py`](app-stacks.py:1)                            | Main deployment entry point | **Start here for manual deployment** |
| [`pipeline_stack.py`](infrastructure/lib/pipeline_stack.py:1) | CI/CD pipeline              | For automated deployments            |
| [`requirements.txt`](requirements.txt:1)                      | Python dependencies         | Install before deploying             |
| [`cdk.json`](cdk.json:1)                                      | CDK configuration           | Modify for custom settings           |

## 🚨 Common Issues and Solutions

1. **"cdk: command not found"**

   ```bash
   npm install -g aws-cdk
   ```

2. **Bootstrap errors**

   ```bash
   cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION
   ```

3. **Permission denied**
   Make sure your AWS user has AdministratorAccess policy

## 📞 Support

For issues and feature requests, please create an issue in the GitHub repository.
