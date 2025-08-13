# Security Lake and SIEM Integration Documentation

This document provides a comprehensive overview of the Security Lake and SIEM (Security Information and Event Management) integration within the multi-region e-commerce platform. It covers the architecture, components, configuration, deployment, and operational aspects of the solution.

## 1. Overview and Architecture

The security solution is designed to provide a centralized, scalable, and cost-effective way to collect, store, and analyze security data from across the AWS organization. It leverages Amazon Security Lake to normalize security logs into the Open Cybersecurity Schema Framework (OCSF) and integrates with various SIEM solutions for threat detection and analysis.

### 1.1. High-Level Architecture

The architecture is composed of three main layers: the security baseline, the Security Lake, and the SIEM sinks.

```
+-------------------------------------------------------------------------------------------------+
|                                       AWS Organization                                          |
|                                                                                                 |
|  +---------------------------+      +---------------------------+      +---------------------------+  |
|  |      Member Account 1     |      |      Member Account 2     |      |      Member Account N     |  |
|  | (e.g., ap-southeast-2)    |      | (e.g., us-west-2)         |      |                           |  |
|  |                           |      |                           |      |                           |  |
|  |  - AWS Services           |      |  - AWS Services           |      |  - ...                    |  |
|  |  - Applications           |      |  - Applications           |      |                           |  |
|  +---------------------------+      +---------------------------+      +---------------------------+  |
|           |      |      |                    |      |      |                    |                      |
|           |      |      +--------------------+      |      +--------------------+                      |
|           |      +----------------------------------+      |                                          |
|           |                                                |                                          |
|  +--------v-----------------------------------------------+----------------------------------------+  |
|  |                                     Security Account                                            |  |
|  |                                                                                                 |  |
|  |  +-------------------------------------------------------------------------------------------+  |  |
|  |  |                                 Amazon Security Lake                                      |  |  |
|  |  |                                                                                           |  |  |
|  |  |  +-----------------------+      +-----------------------+      +-----------------------+  |  |  |
|  |  |  |   VPC Flow Logs       |      |   CloudTrail Events   |      |   Route 53 Logs       |  |  |  |
|  |  |  +-----------------------+      +-----------------------+      +-----------------------+  |  |  |
|  |  |           |                              |                              |                 |  |  |
|  |  |           +------------------------------+------------------------------+                 |  |  |
|  |  |                                          |                                                |  |  |
|  |  |                                          v                                                |  |  |
|  |  |  +-------------------------------------------------------------------------------------+  |  |  |
|  |  |  |                S3 Data Lake Bucket (OCSF Format, Parquet)                         |  |  |  |
|  |  |  +-------------------------------------------------------------------------------------+  |  |  |
|  |  |                                          |                                                |  |  |
|  |  +------------------------------------------+------------------------------------------------+  |  |
|  |                                             |                                                   |  |
|  |                                             v                                                   |  |
|  |  +-------------------------------------------------------------------------------------------+  |  |
|  |  |                                     SIEM Sinks                                          |  |  |
|  |  |                                                                                           |  |  |
|  |  |  +-----------------------+      +-----------------------+      +-----------------------+  |  |  |
|  |  |  |   OpenSearch Sink     |      |     Splunk Sink       |      |      Elastic Sink     |  |  |  |
|  |  |  | (AOSS Collection)     |      | (Kinesis Firehose)    |      | (Kinesis Firehose)    |  |  |  |
|  |  |  +-----------------------+      +-----------------------+      +-----------------------+  |  |  |
|  |  |                                                                                           |  |  |
|  |  +-------------------------------------------------------------------------------------------+  |  |
|  |                                                                                                 |  |
|  +-------------------------------------------------------------------------------------------------+  |
|                                                                                                 |
+-------------------------------------------------------------------------------------------------+
```

### 1.2. Data Flow

1.  **Data Generation**: AWS services (like VPC, CloudTrail, Route 53) and custom applications across all member accounts and regions generate security logs and events.
2.  **Centralized Collection**: Amazon Security Lake is enabled in a designated `securityAccountId`. It automatically collects and centralizes security data from the entire AWS Organization.
3.  **Normalization to OCSF**: As data is ingested, Security Lake automatically normalizes it into the **Open Cybersecurity Schema Framework (OCSF)** format and stores it in a centralized S3 bucket as Parquet files. This provides a standardized, open-source schema for security data.
4.  **Data Partitioning**: The data in the S3 data lake is partitioned by `region`, `accountid`, and `eventday` for efficient querying and cost management.
5.  **SIEM Ingestion**: A configurable SIEM sink subscribes to the Security Lake data.
    - **OpenSearch**: A Security Lake subscriber is created with permissions to the OpenSearch Serverless collection, allowing for direct querying and analysis.
    - **Splunk/Elastic**: A Kinesis Firehose delivery stream is configured to pull data from the Security Lake S3 bucket and forward it to the respective SIEM's HTTP Event Collector (HEC) endpoint.
6.  **Analysis and Alerting**: The SIEM solution is used for advanced analysis, dashboarding, threat hunting, and alerting on the normalized security data.

### 1.3. OCSF (Open Cybersecurity Schema Framework)

OCSF is an open standard for normalizing security telemetry across a wide range of security products and services. By converting logs to the OCSF format, Security Lake simplifies the process of analyzing security data.

Key benefits of OCSF in this architecture:

- **Standardized Schema**: You can write queries and build analytics that work across different data sources without needing to understand the original log formats.
- **Simplified Analytics**: Reduces the effort required for data transformation and enrichment.
- **Vendor-Neutral**: As an open standard, it prevents vendor lock-in and promotes interoperability.

The data in the Security Lake is organized according to OCSF event classes, such as `API Activity`, `Network Activity`, `Authentication Events`, etc. This is reflected in the Glue Data Catalog tables created by Security Lake.

## 2. Components Description

The solution is modular and deployed as a set of AWS CDK stacks. Each stack has a specific responsibility.

### 2.1. `SecurityBaselineStack`

This stack ([`infrastructure/lib/security/security_baseline_stack.py`](infrastructure/lib/security/security_baseline_stack.py:1)) establishes the foundational security services across the AWS Organization. It is deployed to the `securityAccountId` and configured to be the delegated administrator for these services.

- **AWS GuardDuty**: Enabled organization-wide to provide intelligent threat detection. It monitors for malicious activity and unauthorized behavior.
- **AWS Security Hub**: Centralizes security findings from various AWS services (including GuardDuty, Config, and Inspector) and third-party products. It runs automated security checks against the AWS Foundational Security Best Practices and CIS AWS Foundations Benchmark standards.
- **Amazon Detective**: Automatically collects log data from your AWS resources to help you analyze, investigate, and quickly identify the root cause of potential security issues.
- **AWS Config**: Enables AWS Config rules and conformance packs to continuously monitor and record your AWS resource configurations and allows you to automate the evaluation of recorded configurations against desired configurations.
- **CloudWatch Alarms**: Pre-configured alarms for high-severity GuardDuty findings and critical Security Hub findings, which notify a security team via an SNS topic.

### 2.2. `SecurityLakeStack`

This stack ([`infrastructure/lib/security/security_lake_stack.py`](infrastructure/lib/security/security_lake_stack.py:1)) provisions and configures the Amazon Security Lake service.

- **Security Lake**: The core of the solution. It automates the collection and management of your security data at scale.
- **Data Sources**: Configured to collect data from key sources:
  - AWS CloudTrail (management and data events)
  - VPC Flow Logs
  - Route 53 Resolver Query Logs
  - S3 Server Access Logs
  - EKS Audit Logs (optional, via feature flag)
- **S3 Data Lake Bucket**: A central, encrypted S3 bucket to store the normalized OCSF data. It includes lifecycle policies for cost-effective data retention (Intelligent-Tiering and Glacier).
- **Glue Data Catalog**: Creates a Glue database and tables for the OCSF schema, enabling you to easily query the data using services like Amazon Athena.
- **IAM Roles**: Defines the necessary IAM roles for the Security Lake service itself and for subscribers who need to access the data.

### 2.3. `SiemSinksStack`

This stack ([`infrastructure/lib/security/siem_sinks_stack.py`](infrastructure/lib/security/siem_sinks_stack.py:1)) provides a pluggable mechanism to forward the normalized security data from the Security Lake to a SIEM of your choice. It uses a factory pattern to create the appropriate resources based on the `sinkType` context variable.

- **OpenSearch Sink**:
  - Provisions an **Amazon OpenSearch Serverless** collection.
  - Creates a Security Lake subscriber that grants the collection access to the Security Lake data.
  - This is the most direct integration, allowing you to query and visualize the OCSF data within the AWS ecosystem.
- **Splunk Sink**:
  - Provisions a **Kinesis Firehose** delivery stream.
  - The Firehose stream is configured to send data to a Splunk HTTP Event Collector (HEC) endpoint.
  - Requires you to pre-configure the Splunk HEC URL and token in AWS Systems Manager (SSM) Parameter Store.
- **Elastic Sink**:
  - Also uses a **Kinesis Firehose** delivery stream.
  - Configured to send data to an Elastic Cloud endpoint.
  - Requires the Elastic endpoint, username, and password to be stored in SSM Parameter Store.

## 3. Configuration and Context Flags

The behavior of the security stacks is controlled by context variables defined in the `cdk.json` file. These flags allow you to customize the deployment for your specific environment.

### 3.1. General Configuration

| Context Variable             | Type       | Description                                                                                                                                                                                            | Default Value                     |
| ---------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- |
| `orgDelegatedAdminAccountId` | `String`   | The AWS account ID of the organization's delegated administrator for security services. This account will have permissions to manage services like GuardDuty and Security Hub across the organization. | `null`                            |
| `securityAccountId`          | `String`   | The AWS account ID where the centralized security services (like Security Lake and SIEM sinks) are deployed.                                                                                           | `null`                            |
| `loggingAccountId`           | `String`   | The AWS account ID designated for collecting and storing logs from across the organization. (Currently unused, reserved for future use).                                                               | `null`                            |
| `regions`                    | `String[]` | A list of AWS regions where the security infrastructure will be deployed. This should align with your multi-region application footprint.                                                              | `["ap-southeast-2", "us-west-2"]` |

### 3.2. SIEM Sink Configuration

| Context Variable | Type      | Description -                                                                                                                                                                                                                                      |
| ---------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `sinkType`       | `String`  | The type of SIEM sink to use for security event forwarding. This determines which set of resources is created by the `SiemSinksStack`. -                                                                                                           |
| `enableEksAudit` | `Boolean` | A feature flag to enable or disable the collection of EKS audit logs in Security Lake. When `true`, the `SecurityLakeStack` will configure EKS audit logs as a data source. This can increase costs and data volume, so it is disabled by default. | `false` |

### 3.3. How to Configure Each Sink Type

To switch between SIEM sinks, you only need to change the value of the `sinkType` context variable in `cdk.json` and redeploy the `SiemSinksStack`.

- **For `opensearch`**:

  - No additional configuration is required beyond setting `"sinkType": "opensearch"`. The stack will automatically provision the necessary OpenSearch Serverless resources.

- **For `splunk`**:

  1.  Set `"sinkType": "splunk"`.
  2.  You must store the Splunk HEC URL and token in AWS Systems Manager Parameter Store as `SecureString` parameters:
      - `/sec/splunk/hecUrl`: The full URL of your Splunk HEC endpoint.
      - `/sec/splunk/hecToken`: The HEC token for authentication.

- **For `elastic`**:
  1.  Set `"sinkType": "elastic"`.
  2.  You must store your Elastic Cloud credentials in AWS Systems Manager Parameter Store as `SecureString` parameters:
      - `/sec/elastic/endpoint`: The API endpoint URL for your Elastic Cloud deployment.
      - `/sec/elastic/username`: The username for authentication.
      - `/sec/elastic/password`: The password for authentication.

### 3.4. Regional Deployment Considerations

The `regions` context variable allows you to specify which AWS regions the security stacks will be deployed to. This is critical for a multi-region architecture.

- The `SecurityBaselineStack` and `SecurityLakeStack` should be deployed to all regions where you have workloads.
- The `SiemSinksStack` is typically deployed in the primary region, as it centralizes the data from all other regions.
- Security Lake's cross-region replication feature ensures that data from all regional deployments is consolidated into the primary region's S3 bucket before being sent to the SIEM.

## 4. Deployment Instructions

Follow these steps to deploy the Security Lake and SIEM integration solution.

### 4.1. Prerequisites

1.  **AWS CDK**: Ensure you have the AWS CDK CLI installed and configured.
2.  **Python**: The CDK application is written in Python. Make sure you have Python 3.8+ and `pip` installed.
3.  **AWS Credentials**: Configure your AWS credentials with permissions to deploy the necessary resources. It's recommended to use a profile: `aws configure --profile <your-profile-name>`.
4.  **Node.js**: The AWS CDK requires Node.js.
5.  **Virtual Environment**: It is highly recommended to use a Python virtual environment.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

### 4.2. Account Setup

1.  **Identify Account IDs**: Determine the AWS account IDs for your `orgDelegatedAdminAccountId` and `securityAccountId`.
2.  **Update `cdk.json`**: Open the [`cdk.json`](cdk.json) file and fill in the required context variables:
    - `orgDelegatedAdminAccountId`
    - `securityAccountId`
    - `regions` (if different from the default)
3.  **Configure SIEM Parameters (if applicable)**: If you are using the `splunk` or `elastic` sink, ensure you have created the necessary `SecureString` parameters in AWS Systems Manager Parameter Store as described in the configuration section.

### 4.3. Step-by-Step Deployment Process

The stacks should be deployed in the following order.

**Step 1: Deploy the `SecurityBaselineStack`**

This stack sets up the foundational security services. Deploy it to your designated security account.

```bash
cdk deploy SecurityBaselineStack --profile <your-profile-name> -c orgDelegatedAdminAccountId=<org-admin-acct-id> -c securityAccountId=<sec-acct-id>
```

**Step 2: Deploy the `SecurityLakeStack`**

This stack provisions the Security Lake. Deploy it to each region specified in your `regions` list.

For the primary region:

```bash
cdk deploy SecurityLakeStack --profile <your-profile-name> -c securityAccountId=<sec-acct-id> --region <primary-region>
```

For each secondary region:

```bash
cdk deploy SecurityLakeStack --profile <your-profile-name> -c securityAccountId=<sec-acct-id> --region <secondary-region>
```

**Step 3: Deploy the `SiemSinksStack`**

This stack deploys the SIEM integration. It should be deployed to the **primary region** only.

- **For OpenSearch (default):**

  ```bash
  cdk deploy SiemSinksStack --profile <your-profile-name> -c sinkType=opensearch --region <primary-region>
  ```

- **For Splunk:**

  ```bash
  cdk deploy SiemSinksStack --profile <your-profile-name> -c sinkType=splunk --region <primary-region>
  ```

- **For Elastic:**

  ```bash
  cdk deploy SiemSinksStack --profile <your-profile-name> -c sinkType=elastic --region <primary-region>
  ```

### 4.4. How to Switch Between Sink Types

You can easily switch the SIEM integration without redeploying the other stacks.

1.  **Update `cdk.json`**: Change the `sinkType` value to your desired sink (`opensearch`, `splunk`, or `elastic`).
2.  **Redeploy `SiemSinksStack`**: Run the `cdk deploy` command for the `SiemSinksStack` again with the updated context. The CDK will automatically handle the creation of the new sink and the destruction of the old one.

    For example, to switch from Splunk to OpenSearch:

    ```bash
    # First, update cdk.json: "sinkType": "opensearch"
    cdk deploy SiemSinksStack --profile <your-profile-name> -c sinkType=opensearch --region <primary-region>
    ```

## 5. SIEM Sink Details

This section provides detailed information about configuring and using each of the supported SIEM sinks.

### 5.1. OpenSearch Serverless

The OpenSearch sink is the most tightly integrated option, keeping all data and analytics within the AWS ecosystem.

- **Collection Setup**: The `SiemSinksStack` automatically provisions an **Amazon OpenSearch Serverless** collection with the name `security-lake-collection`. It's configured as a `TIMESERIES` collection, which is optimized for log analytics.
- **Dashboards and Querying**:
  - You can access the OpenSearch Dashboards for your collection directly from the AWS Management Console.
  - The data is indexed by date, and you can create index patterns like `security-lake-collection*` to query the data.
  - You can build custom dashboards and visualizations to monitor security events.
- **Authentication**: Access to the OpenSearch collection is controlled by an access policy that grants permissions to the Security Lake subscriber role. This ensures that only authorized principals can read and write data.

### 5.2. Splunk

The Splunk sink uses Kinesis Firehose to forward data to a Splunk HTTP Event Collector (HEC).

- **HEC Configuration**:
  - Before deploying, you must have a Splunk HEC endpoint and token.
  - The HEC endpoint URL and token must be stored as `SecureString` parameters in **AWS Systems Manager Parameter Store** under the names `/sec/splunk/hecUrl` and `/sec/splunk/hecToken`, respectively.
- **Kinesis Firehose**:
  - A Firehose delivery stream named `SplunkDeliveryStream` is created.
  - It's configured to buffer data and send it to the Splunk HEC in `Raw` format.
  - **Buffering**: You can configure buffering hints in the CDK stack to optimize the batching of data sent to Splunk, which can help with performance and cost.
- **Monitoring**: The stack creates CloudWatch alarms to monitor the Firehose delivery stream for errors (4xx and 5xx). If data fails to be delivered to Splunk, it will be backed up to a dedicated S3 bucket for later analysis or reprocessing.

### 5.3. Elastic

The Elastic sink is similar to the Splunk sink, using Kinesis Firehose to send data to an Elastic Cloud endpoint.

- **Cloud Integration**:
  - You need an Elastic Cloud deployment with an API endpoint that can receive data.
  - The endpoint URL, username, and password must be stored as `SecureString` parameters in **AWS Systems Manager Parameter Store**:
    - `/sec/elastic/endpoint`
    - `/sec/elastic/username`
    - `/sec/elastic/password`
- **Authentication**: The Firehose delivery stream is configured to use Basic Authentication. It constructs the `Authorization` header using the username and password from SSM.
- **Error Handling**: Like the Splunk sink, a backup S3 bucket is created. If Firehose is unable to deliver data to the Elastic endpoint, the failed records will be stored in this bucket. CloudWatch alarms are also created to notify you of delivery failures.

## 6. Monitoring and Operations

Effective monitoring is crucial for ensuring the reliability and performance of the security data pipeline.

### 6.1. CloudWatch Dashboards and Alarms

The solution comes with pre-configured CloudWatch alarms to notify you of potential issues.

- **`SecurityBaselineStack` Alarms**:

  - `HighSeverityGuardDutyFindings`: Triggers when GuardDuty detects a high-severity finding.
  - `CriticalSecurityHubFindings`: Triggers when Security Hub reports a critical-severity finding.
  - These alarms send notifications to the email address provided during stack deployment.

- **`SecurityLakeStack` Alarms**:

  - `SecurityLakeDataFreshnessAlarm`: Triggers if no new data has been written to the lake for a specified period (e.g., 24 hours). This could indicate an issue with the data collection process.
  - `SecurityLakeIngestionErrorsAlarm`: Triggers if there are failures in the data ingestion process.

- **`SiemSinksStack` Alarms**:
  - For Splunk and Elastic sinks, alarms are created to monitor the Kinesis Firehose delivery stream for `4xx` (client-side) and `5xx` (server-side) errors.
  - These alarms indicate problems with delivering data to your SIEM endpoint.

### 6.2. Key Metrics to Monitor

- **Amazon Security Lake**:
  - `s3ObjectCount`: Monitor the number of S3 objects being added to the lake. A sudden drop could indicate an issue.
  - `secondsSinceLastS3Object`: Tracks the time since the last object was written.
- **Kinesis Firehose (for Splunk/Elastic)**:
  - `DeliveryToHttpEndpoint.Success`: A value of `0` for an extended period indicates a delivery failure.
  - `DeliveryToHttpEndpoint.Records`: The number of records delivered to the SIEM.
  - `DeliveryToS3.Bytes`: The number of bytes written to the backup S3 bucket. A high value here indicates persistent delivery failures.
- **AWS Lambda (if custom processors are added)**:
  - `Invocations`: The number of times the function is invoked.
  - `Errors`: The number of failed invocations.
  - `Duration`: The execution time of the function.

### 6.3. Troubleshooting Common Issues

- **No data in SIEM**:
  1.  Check the CloudWatch alarms for the `SiemSinksStack`.
  2.  Inspect the Kinesis Firehose delivery stream logs in CloudWatch for detailed error messages.
  3.  Verify that the SIEM endpoint is accessible and that the credentials in SSM Parameter Store are correct.
  4.  Check the backup S3 bucket for failed records. The error messages associated with these records can provide clues.
- **No new data in Security Lake**:
  1.  Check the `SecurityLakeDataFreshnessAlarm`.
  2.  Verify that the data sources (CloudTrail, VPC Flow Logs, etc.) are correctly configured and enabled in the member accounts.
  3.  Check the IAM permissions for the Security Lake service role.
- **CDK Deployment Failures**:
  1.  Review the CloudFormation events in the AWS Management Console for detailed error messages.
  2.  Ensure that the context variables in `cdk.json` are correctly set.
  3.  Verify that the AWS credentials used for deployment have sufficient permissions.

### 6.4. Log Locations

- **Security Lake Logs**: The raw and normalized logs are stored in the central S3 data lake bucket, partitioned by region, account, and day.
- **Kinesis Firehose Logs**: Delivery stream error logs are sent to a dedicated CloudWatch Log Group, which will be named something like `/aws/kinesisfirehose/YourDeliveryStreamName`.
- **CloudTrail Logs**: All CDK and AWS API calls are logged in CloudTrail, which is an invaluable resource for debugging deployment and permission issues.

## 7. Security Considerations

Security is a foundational aspect of this solution. The following considerations have been implemented to protect the data and infrastructure.

### 7.1. IAM Roles and Least Privilege Access

- **Principle of Least Privilege**: All IAM roles created by the CDK stacks are scoped with the minimum necessary permissions.
- **Service Roles**: Specific roles are created for services like Kinesis Firehose and Security Lake, ensuring they only have access to the resources they need to manage.
- **Delegated Administration**: The `orgDelegatedAdminAccountId` model is used to separate the management of security services from the day-to-day operational accounts, reducing the risk of unauthorized changes.
- **Subscriber Role**: The `SecurityLakeSubscriberRole` is designed to provide read-only access to the Security Lake data, preventing subscribers from modifying or deleting the raw logs.

### 7.2. Encryption at Rest and in Transit

- **Encryption at Rest**:
  - The Security Lake S3 bucket is encrypted using **AWS Key Management Service (KMS)** with a customer-managed key (`alias/security-lake-key`). This provides an extra layer of security and control over the data.
  - The Kinesis Firehose backup S3 bucket is encrypted with S3-managed keys (SSE-S3).
- **Encryption in Transit**:
  - All communication between AWS services (e.g., from data sources to Security Lake, from Security Lake to Kinesis Firehose) is encrypted using TLS.
  - When configuring Splunk or Elastic sinks, it is critical to use `https://` endpoints to ensure that data sent from Firehose to your SIEM is encrypted in transit.

### 7.3. Cross-Account Access Patterns

- **Resource-Based Policies**: The solution uses resource-based policies (e.g., S3 bucket policies, KMS key policies) to grant cross-account access. This is more secure and manageable than using IAM roles for all cross-account interactions.
- **External IDs**: When creating subscribers for Security Lake, an external ID (which is the AWS account ID) is used to mitigate the "confused deputy" problem.

### 7.4. Compliance and Audit Considerations

- **Immutable Data**: The Security Lake S3 bucket has versioning enabled, which helps preserve an immutable record of all security logs. This is important for compliance and forensic investigations.
- **OCSF Standard**: The use of the OCSF standard helps with compliance by providing a consistent and well-documented format for security data.
- **AWS Config Conformance Packs**: The `SecurityBaselineStack` can be extended to include AWS Config conformance packs for standards like PCI-DSS, HIPAA, or NIST, which automate compliance checking.
- **Audit Trail**: All actions performed by the CDK and the security services are logged in AWS CloudTrail, providing a comprehensive audit trail.

## 8. Example Queries

This section provides example queries to help you start analyzing your security data.

### 8.1. Athena Queries

You can query the OCSF tables directly from the AWS Management Console using Amazon Athena.

**Query 1: Count CloudTrail Events by Event Name**

This query helps you understand the most frequent API activities in your environment.

```sql
SELECT
    event_name,
    COUNT(*) AS event_count
FROM
    "security_lake_db"."ocsf_table"
WHERE
    eventday = '2023-10-27' -- Replace with the desired date
    AND metadata.product.name = 'CloudTrail'
GROUP BY
    event_name
ORDER BY
    event_count DESC;
```

**Query 2: Find Failed Console Logins**

This query identifies failed login attempts to the AWS Management Console.

```sql
SELECT
    time,
    actor.user.name AS user_name,
    src_endpoint.ip AS source_ip,
    status_detail
FROM
    "security_lake_db"."ocsf_table"
WHERE
    eventday = '2023-10-27'
    AND metadata.product.name = 'CloudTrail'
    AND event_name = 'ConsoleLogin'
    AND status = 'Failure';
```

**Query 3: Top 10 Source IPs for VPC Flow Logs**

This query shows the most active source IP addresses based on VPC Flow Log data.

```sql
SELECT
    src_endpoint.ip AS source_ip,
    SUM(traffic.bytes) AS total_bytes
FROM
    "security_lake_db"."ocsf_table"
WHERE
    eventday = '2023-10-27'
    AND metadata.product.name = 'VPC Flow Logs'
GROUP BY
    src_endpoint.ip
ORDER BY
    total_bytes DESC
LIMIT 10;
```

### 8.2. OpenSearch Example Queries

If you are using the OpenSearch sink, you can use the OpenSearch Dashboards to query and visualize the data.

**Query 1: Find all documents related to a specific user**

This query uses the OpenSearch Query DSL to search for all activities associated with a specific IAM user.

```json
{
  "query": {
    "match": {
      "actor.user.name": "your-iam-user-name"
    }
  }
}
```

**Query 2: Search for SSH traffic**

This query identifies network traffic on port 22 (SSH).

```json
{
  "query": {
    "bool": {
      "must": [{ "match": { "dst_endpoint.port": 22 } }]
    }
  }
}
```

**Query 3: Visualize API calls over time**

1.  In OpenSearch Dashboards, go to the **Visualize** library and create a new visualization.
2.  Choose a **Line** chart.
3.  Select your index pattern (e.g., `security-lake-collection*`).
4.  For the Y-axis, use a `Count` aggregation.
5.  For the X-axis, use a `Date Histogram` aggregation on the `time` field.
6.  This will create a chart showing the volume of API calls over time. You can add filters to narrow down the data to specific event names or users.

## 9. Cost Optimization

Managing costs is an important aspect of any cloud solution. Here are some strategies for optimizing the costs of your Security Lake implementation.

### 9.1. S3 Lifecycle Policies

- **Intelligent-Tiering**: The Security Lake S3 bucket is configured with a lifecycle policy to move data to the **S3 Intelligent-Tiering** storage class after 30 days. This automatically moves data to the most cost-effective access tier without performance impact or operational overhead.
- **Glacier**: After 365 days, data is transitioned to **S3 Glacier**, which is a low-cost storage class designed for long-term archiving. This is ideal for meeting long-term compliance requirements.
- **Customization**: You can customize these lifecycle policies in the `SecurityLakeStack` to match your organization's data retention and access requirements.

### 9.2. Data Retention Strategies

- **Selective Logging**: While Security Lake makes it easy to collect all logs, consider being selective about which data sources you enable. For example, if you don't use EKS, you can keep `enableEksAudit` set to `false`.
- **Data Source Filtering**: For some services, you can filter the logs at the source. For example, you can configure CloudTrail trails to log only management events if you don't need data events.
- **SIEM Indexing**: In your SIEM solution (Splunk, Elastic, or OpenSearch), be strategic about which data you index. Not all data needs to be immediately searchable. You can keep the raw logs in the Security Lake for long-term storage and only index the most critical data in your SIEM.

### 9.3. Regional Considerations for Cost

- **Data Transfer Costs**: Be mindful of data transfer costs between regions. Security Lake's cross-region replication will incur data transfer charges.
- **Primary Region Selection**: Choose your primary region carefully. It's often most cost-effective to select the region where the majority of your data is generated to minimize cross-region data transfer.
- **Querying Costs**: When using Athena, you are charged based on the amount of data scanned. The Parquet file format and partitioning used by Security Lake help reduce query costs, but it's still important to write efficient queries that limit the amount of data scanned.

## 10. Verification and Testing

After deploying the stacks, it's important to verify that everything is working correctly.

### 10.1. How to Verify Successful Deployment

1.  **Check CloudFormation Outputs**: After each `cdk deploy` command, check the outputs of the CloudFormation stack in the AWS Management Console. This will give you the ARNs and names of the created resources.
2.  **Verify Security Lake Status**: In the Amazon Security Lake console, check the status of your data lake and ensure that the data sources you enabled are active.
3.  **Check S3 Bucket**: Navigate to the Security Lake S3 bucket and verify that data is being written to it. You should see a folder structure organized by region, account ID, and date.
4.  **Inspect Glue Catalog**: In the AWS Glue console, verify that the `security_lake_db` database and the `ocsf_table` table have been created.
5.  **Check SIEM Sink**:
    - **OpenSearch**: Go to the OpenSearch Serverless console and check the status of your collection.
    - **Splunk/Elastic**: Go to the Kinesis Firehose console and check the status of your delivery stream. The status should be "Active".

### 10.2. Test Data Ingestion

To test the end-to-end data flow, you can generate some test events.

1.  **Log in to the AWS Console**: Log in to the AWS Management Console in one of the member accounts. This will generate a `ConsoleLogin` event in CloudTrail.
2.  **Create and Delete a Resource**: Create and then delete a simple resource, like an S3 bucket. This will generate `CreateBucket` and `DeleteBucket` API calls.
3.  **Wait for Data to Flow**: It may take some time (up to 15-20 minutes) for the data to flow through the entire pipeline.
4.  **Query the Data**: Use the Athena or OpenSearch queries from the "Example Queries" section to find the test events you generated.

### 10.3. Validate SIEM Sink Connectivity

- **OpenSearch**:
  - Use the OpenSearch Dashboards to search for the test events.
- **Splunk/Elastic**:
  1.  Log in to your Splunk or Elastic instance.
  2.  Search for the events you generated.
  3.  If you don't see the data, check the Kinesis Firehose monitoring tab in the AWS console for any delivery errors.
  4.  Inspect the CloudWatch logs for the Firehose delivery stream for detailed error messages.
