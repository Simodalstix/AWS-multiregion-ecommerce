from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms,
    aws_glue as glue,
    aws_securitylake as securitylake,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    CfnOutput,
    Duration,
    Tags,
)
from constructs import Construct


class SecurityLakeStack(Stack):
    """
    This stack provisions the Amazon Security Lake service, including:
    - Delegated administrator setup
    - Configuration of data sources (CloudTrail, VPC Flow Logs, etc.)
    - S3 bucket for the data lake with cross-region replication
    - Glue Data Catalog for OCSF schema
    - IAM roles for service operation and data access
    - CloudWatch monitoring for ingestion and data freshness
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        primary_region: str,
        secondary_region: str,
        security_admin_account_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Context flags
        enable_eks_audit = self.node.try_get_context("enableEksAudit")

        # KMS Key for Security Lake
        kms_key = kms.Key(
            self,
            "SecurityLakeKmsKey",
            description="KMS key for Security Lake encryption",
            enable_key_rotation=True,
            alias="alias/security-lake-key",
        )

        # S3 bucket for the data lake
        data_lake_bucket = s3.Bucket(
            self,
            "SecurityLakeBucket",
            bucket_name=f"aws-security-lake-bucket-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="IntelligentTiering",
                    status=s3.LifecycleRuleStatus.ENABLED,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30),
                        )
                    ],
                ),
                s3.LifecycleRule(
                    id="Glacier",
                    status=s3.LifecycleRuleStatus.ENABLED,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(365),
                        )
                    ],
                ),
            ],
        )

        # Security Lake custom channel
        security_lake_channel = securitylake.CfnCustomLogSource(
            self,
            "SecurityLakeCustomChannel",
            source_name="ECommercePlatform",
            source_version="1.0",
            log_provider_account_id=self.account,
        )

        # Configure Security Lake
        security_lake = securitylake.CfnDataLake(
            self,
            "SecurityLake",
            meta_store_manager_role_arn=self.format_arn(
                service="iam",
                region="",
                account=self.account,
                resource="role",
                resource_name="AWSServiceRoleForSecurityLake",
            ),
            configuration=securitylake.CfnDataLake.ConfigurationProperty(
                region=self.region,
                encryption_configuration=securitylake.CfnDataLake.EncryptionConfigurationProperty(
                    kms_key_id=kms_key.key_id
                ),
                replication_configuration=securitylake.CfnDataLake.ReplicationConfigurationProperty(
                    region=secondary_region,
                    role_arn=None,  # Role will be created by the service
                ),
            ),
        )

        # Set up delegated admin for Security Lake
        delegated_admin = securitylake.CfnDelegatedAdmin(
            self, "SecurityLakeDelegatedAdmin", account_id=security_admin_account_id
        )

        # Enable CloudTrail data source
        cloudtrail_source = securitylake.CfnAwsLogSource(
            self,
            "CloudTrailLogSource",
            data_lake_arn=security_lake.attr_arn,
            source_name="CLOUD_TRAIL_MGMT_AND_DATA_EVENTS",
            source_version="1.0",
            accounts=[self.account],
        )

        # Enable VPC Flow Logs data source
        vpc_flow_logs_source = securitylake.CfnAwsLogSource(
            self,
            "VpcFlowLogsSource",
            data_lake_arn=security_lake.attr_arn,
            source_name="VPC_FLOW_LOGS",
            source_version="1.0",
            accounts=[self.account],
        )

        # Enable Route 53 Resolver query logs data source
        route53_source = securitylake.CfnAwsLogSource(
            self,
            "Route53LogSource",
            data_lake_arn=security_lake.attr_arn,
            source_name="ROUTE53_RESOLVER_QUERY_LOGS",
            source_version="1.0",
            accounts=[self.account],
        )

        # Enable S3 server access logs data source
        s3_access_logs_source = securitylake.CfnAwsLogSource(
            self,
            "S3AccessLogsSource",
            data_lake_arn=security_lake.attr_arn,
            source_name="S3_SERVER_ACCESS_LOGS",
            source_version="1.0",
            accounts=[self.account],
        )

        # Glue database for Security Lake
        glue_database = glue.CfnDatabase(
            self,
            "SecurityLakeGlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="security_lake_db",
                description="Database for Security Lake OCSF data",
            ),
        )

        # Glue table for OCSF schema
        glue_table = glue.CfnTable(
            self,
            "SecurityLakeGlueTable",
            catalog_id=self.account,
            database_name=glue_database.database_input.name,
            table_input=glue.CfnTable.TableInputProperty(
                name="ocsf_table",
                description="Table for OCSF schema in Security Lake",
                table_type="EXTERNAL_TABLE",
                parameters={"classification": "ocsf"},
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    location=f"s3://{data_lake_bucket.bucket_name}/",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.openx.data.jsonserde.JsonSerDe",
                        parameters={"paths": "true"},
                    ),
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(name="region", type="string"),
                    glue.CfnTable.ColumnProperty(name="accountid", type="string"),
                    glue.CfnTable.ColumnProperty(name="eventday", type="string"),
                ],
            ),
        )

        # IAM role for Security Lake subscribers
        subscriber_role = iam.Role(
            self,
            "SecurityLakeSubscriberRole",
            assumed_by=iam.AccountPrincipal(security_admin_account_id),
            role_name="SecurityLakeSubscriberRole",
            description="Role for subscribers to access Security Lake data",
        )

        data_lake_bucket.grant_read(subscriber_role)
        kms_key.grant_decrypt(subscriber_role)

        subscriber_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetPartitions",
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                ],
                resources=[
                    glue_database.ref,
                    glue_table.ref,
                    f"arn:aws:athena:{self.region}:{self.account}:workgroup/primary",
                ],
            )
        )

        # CloudWatch monitoring for Security Lake
        security_topic = sns.Topic(self, "SecurityLakeAlertsTopic")

        cloudwatch.Alarm(
            self,
            "SecurityLakeDataFreshnessAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/SecurityLake",
                metric_name="secondsSinceLastS3Object",
                dimensions_map={"dataLakeArn": security_lake.attr_arn},
            ),
            threshold=Duration.hours(24).to_seconds(),
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm for when Security Lake data is not fresh",
            actions_enabled=True,
        ).add_alarm_action(cloudwatch_actions.SnsAction(security_topic))

        cloudwatch.Alarm(
            self,
            "SecurityLakeIngestionErrorsAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/SecurityLake",
                metric_name="s3ObjectCount",
                dimensions_map={
                    "dataLakeArn": security_lake.attr_arn,
                    "status": "FAILED",
                },
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm for Security Lake ingestion errors",
            actions_enabled=True,
        ).add_alarm_action(cloudwatch_actions.SnsAction(security_topic))

        # Add tags to all resources in the stack
        Tags.of(self).add("Project", "Ecommerce")
        Tags.of(self).add("Stack", "SecurityLake")

        # Outputs
        CfnOutput(
            self,
            "SecurityLakeBucketName",
            value=data_lake_bucket.bucket_name,
            description="Name of the S3 bucket for Security Lake",
        )
        CfnOutput(
            self,
            "SecurityLakeGlueDatabaseName",
            value=glue_database.database_input.name,
            description="Name of the Glue database for Security Lake",
        )
        CfnOutput(
            self,
            "SubscriberRoleArn",
            value=subscriber_role.role_arn,
            description="ARN of the IAM role for Security Lake subscribers",
        )

        # Enable EKS audit logs data source if flag is set
        if enable_eks_audit:
            eks_audit_source = securitylake.CfnAwsLogSource(
                self,
                "EksAuditLogSource",
                data_lake_arn=security_lake.attr_arn,
                source_name="EKS_AUDIT_LOGS",
                source_version="1.0",
                accounts=[self.account],
            )
