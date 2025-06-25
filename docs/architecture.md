# Architecture Diagram

```mermaid
graph TB
    subgraph "Primary Region (ap-southeast-2)"
        API1[API Gateway] --> LF1[Lambda Functions]
        LF1 --> DDB1[DynamoDB Global Table]
        LF1 --> EB1[EventBridge]
        EB1 --> SF1[Step Functions]
        SF1 --> LF1
        DDB1 <--> DDB2
        EB1 --> EB2
    end

    subgraph "Secondary Region (us-west-2)"
        API2[API Gateway] --> LF2[Lambda Functions]
        LF2 --> DDB2[DynamoDB Global Table]
        LF2 --> EB2[EventBridge]
        EB2 --> SF2[Step Functions]
        SF2 --> LF2
    end

    R53[Route53] --> API1
    R53 --> API2

    subgraph "CI/CD Pipeline"
        GH[GitHub] --> CP[CodePipeline]
        CP --> CB[CodeBuild]
        CB --> CD1[Deploy Primary]
        CB --> CD2[Deploy Secondary]
    end

    classDef primary fill:#f9f,stroke:#333,stroke-width:2px
    classDef secondary fill:#bbf,stroke:#333,stroke-width:2px
    classDef global fill:#bfb,stroke:#333,stroke-width:2px

    class API1,LF1,EB1,SF1 primary
    class API2,LF2,EB2,SF2 secondary
    class R53,DDB1,DDB2 global
```

## Architecture Overview

This multi-region architecture provides high availability and disaster recovery capabilities through:

1. **Active-Active Configuration**

   - Both regions handle traffic simultaneously
   - Route53 health checks and DNS failover
   - Automatic traffic routing to healthy endpoints

2. **Data Consistency**

   - DynamoDB Global Tables for multi-region data replication
   - Eventually consistent read/write access in both regions
   - Automatic conflict resolution

3. **Event Processing**

   - EventBridge for event routing and processing
   - Cross-region event replication
   - Step Functions for workflow orchestration

4. **CI/CD Pipeline**

   - Automated multi-region deployments
   - Infrastructure as Code using CDK
   - Blue/Green deployment strategy

5. **Monitoring and Observability**
   - CloudWatch metrics and alarms
   - CloudTrail for API auditing
   - X-Ray for distributed tracing
