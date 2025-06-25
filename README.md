# AWS Multi-Region Event-Driven E-commerce Platform

This project demonstrates an advanced, production-ready e-commerce order processing system built with AWS CDK. It showcases event-driven architecture, multi-region disaster recovery, and automated CI/CD pipelines.

## Architecture Overview

### Core Components

- **API Layer**: API Gateway with Lambda integrations for order processing
- **Event Processing**: EventBridge for centralized event routing and processing
- **Data Storage**: DynamoDB Global Tables for multi-region data consistency
- **Workflow Management**: Step Functions for order orchestration
- **Service Mesh**: Multiple microservices handling different aspects of order processing

### Microservices

- Order Service (validation and creation)
- Inventory Service (stock management)
- Payment Service (transaction processing)
- Notification Service (customer communications)
- Shipping Service (fulfillment handling)

### Disaster Recovery

- Active-Active Multi-Region Configuration
- Automatic Failover with Route53 Health Checks
- Cross-Region Event Replication
- Global Data Consistency with DynamoDB Global Tables

### CI/CD Pipeline

- Multi-Region Deployment Strategy
- Automated Testing and Validation
- Blue/Green Deployment Pattern
- Infrastructure as Code with CDK

## Technologies Used

- **Infrastructure**: AWS CDK (Python)
- **Compute**: AWS Lambda, Step Functions
- **Storage**: DynamoDB Global Tables
- **Messaging**: EventBridge
- **API**: API Gateway
- **CI/CD**: CodePipeline, CodeBuild, CodeDeploy
- **DNS**: Route53 with Health Checks
- **Monitoring**: CloudWatch, CloudTrail

## Project Purpose

This project serves as a comprehensive example of building cloud-native, event-driven systems with enterprise-grade reliability. It demonstrates:

- Event-Driven Architecture Patterns
- Multi-Region High Availability
- Infrastructure as Code Best Practices
- Modern CI/CD Workflows
- Production-Ready Service Design

## Getting Started

Detailed setup and deployment instructions can be found in the [Setup Guide](docs/setup.md).

## Architecture Diagram

See [architecture.png](docs/architecture.png) for a visual representation of the system design.

---

For detailed technical documentation and implementation details, see the [Documentation](docs/) directory.
