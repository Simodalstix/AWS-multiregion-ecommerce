from abc import ABC, abstractmethod
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms,
    aws_ssm as ssm,
    aws_opensearchserverless as aoss,
    aws_securitylake as securitylake,
    aws_kinesisfirehose as firehose,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    RemovalPolicy,
    Duration,
    CfnOutput,
    Tags,
)
import json
import base64

from .security_lake_stack import SecurityLakeStack


class SiemSink(ABC):
    """Abstract base class for SIEM sinks."""

    def __init__(
        self, scope: Construct, id: str, security_lake_stack: SecurityLakeStack
    ):
        self.scope = scope
        self.id = id
        self.security_lake_stack = security_lake_stack
        self.stack = Stack.of(scope)

    @abstractmethod
    def create_sink(self):
        """Creates the resources for the SIEM sink."""
        pass

    def _create_backup_bucket(self) -> s3.Bucket:
        """Creates an S3 bucket for backing up failed deliveries."""
        backup_bucket = s3.Bucket(
            self.scope,
            f"{self.id}BackupBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveAfter90Days",
                    enabled=True,
                    expiration=Duration.days(365),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(90),
                        )
                    ],
                )
            ],
        )
        Tags.of(backup_bucket).add("Purpose", "SIEM Sink Backup")
        return backup_bucket

    def _create_firehose_role(self, name: str, backup_bucket: s3.Bucket) -> iam.Role:
        """Creates an IAM role for Kinesis Firehose."""
        firehose_role = iam.Role(
            self.scope,
            f"{self.id}{name}FirehoseRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )

        # Grant permissions to read from Security Lake S3 bucket
        self.security_lake_stack.data_lake_bucket.grant_read(firehose_role)
        self.security_lake_stack.kms_key.grant_decrypt(firehose_role)

        # Grant permissions to write to the backup bucket
        backup_bucket.grant_write(firehose_role)

        return firehose_role

    def _create_cloudwatch_alarms(self, delivery_stream_name: str, sink_type: str):
        """Creates CloudWatch alarms for Firehose delivery errors."""
        alarm_topic = sns.Topic(self.scope, f"{self.id}{sink_type}AlarmTopic")

        # Alarm for 4xx errors
        four_xx_alarm = cloudwatch.Alarm(
            self.scope,
            f"{self.id}{sink_type}4xxErrorsAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/KinesisFirehose",
                metric_name=f"DeliveryTo{sink_type}.Success",
                dimensions_map={"DeliveryStreamName": delivery_stream_name},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarm_description=f"Alarm for {sink_type} delivery 4xx errors.",
        )
        four_xx_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Alarm for 5xx errors
        five_xx_alarm = cloudwatch.Alarm(
            self.scope,
            f"{self.id}{sink_type}5xxErrorsAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/KinesisFirehose",
                metric_name=f"DeliveryTo{sink_type}.HttpEndpoint.Success",
                dimensions_map={"DeliveryStreamName": delivery_stream_name},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarm_description=f"Alarm for {sink_type} delivery 5xx errors.",
        )
        five_xx_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))


class OpenSearchSink(SiemSink):
    """SIEM sink for OpenSearch Serverless."""

    def create_sink(self):
        """Creates an OpenSearch Serverless collection and a Security Lake subscriber."""
        # 1. Create OpenSearch Serverless Collection
        collection = aoss.CfnCollection(
            self.scope,
            "OpenSearchServerlessCollection",
            name="security-lake-collection",
            type="TIMESERIES",
            description="Collection for Security Lake data",
        )

        # 2. Data Access Policy
        access_policy = aoss.CfnAccessPolicy(
            self.scope,
            "OpenSearchAccessPolicy",
            name="security-lake-access-policy",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/{collection.name}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:WriteDocument",
                                ],
                            }
                        ],
                        "Principal": [
                            self.security_lake_stack.subscriber_role.role_arn
                        ],
                    }
                ]
            ),
        )
        access_policy.add_dependency(collection)

        # 3. Security Lake Subscriber
        subscriber = securitylake.CfnSubscriber(
            self.scope,
            "OpenSearchSubscriber",
            data_lake_arn=self.security_lake_stack.security_lake.attr_arn,
            subscriber_identity=securitylake.CfnSubscriber.SubscriberIdentityProperty(
                external_id=self.stack.account,
                principal=self.stack.account,
            ),
            subscriber_name="OpenSearchServerlessSubscriber",
            access_types=["S3"],
            sources=[
                securitylake.CfnSubscriber.SourceProperty(
                    aws_log_source_resource=securitylake.CfnSubscriber.AwsLogSourceResourceProperty(
                        source_name="VPC_FLOW_LOGS", source_version="1.0"
                    )
                ),
                securitylake.CfnSubscriber.SourceProperty(
                    aws_log_source_resource=securitylake.CfnSubscriber.AwsLogSourceResourceProperty(
                        source_name="CLOUD_TRAIL_MGMT_AND_DATA_EVENTS",
                        source_version="1.0",
                    )
                ),
            ],
            subscriber_description="Subscriber for OpenSearch Serverless",
        )
        subscriber.add_dependency(access_policy)

        CfnOutput(
            self.scope,
            "OpenSearchCollectionEndpoint",
            value=collection.attr_collection_endpoint,
        )


class SplunkSink(SiemSink):
    """SIEM sink for Splunk."""

    def create_sink(self):
        """Creates a Kinesis Firehose to deliver data to Splunk HEC."""
        # 1. Get Splunk HEC config from SSM
        hec_url = ssm.StringParameter.from_secure_string_parameter_name(
            self.scope, "SplunkHecUrl", parameter_name="/sec/splunk/hecUrl"
        ).string_value
        hec_token = ssm.StringParameter.from_secure_string_parameter_name(
            self.scope, "SplunkHecToken", parameter_name="/sec/splunk/hecToken"
        ).string_value

        # 2. Create backup bucket and Firehose role
        backup_bucket = self._create_backup_bucket()
        firehose_role = self._create_firehose_role("Splunk", backup_bucket)

        # 3. Create Kinesis Firehose Delivery Stream
        delivery_stream = firehose.CfnDeliveryStream(
            self.scope,
            "SplunkDeliveryStream",
            delivery_stream_type="DirectPut",
            splunk_destination_configuration=firehose.CfnDeliveryStream.SplunkDestinationConfigurationProperty(
                hec_endpoint=hec_url,
                hec_endpoint_type="Raw",
                hec_token=hec_token,
                s3_backup_mode="FailedDataOnly",
                s3_configuration=firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                    bucket_arn=backup_bucket.bucket_arn,
                    role_arn=firehose_role.role_arn,
                    compression_format="GZIP",
                ),
                retry_options=firehose.CfnDeliveryStream.SplunkRetryOptionsProperty(
                    duration_in_seconds=300
                ),
            ),
        )

        # 4. Create CloudWatch Alarms
        self._create_cloudwatch_alarms(delivery_stream.ref, "Splunk")

        CfnOutput(self.scope, "SplunkDeliveryStreamName", value=delivery_stream.ref)


class ElasticSink(SiemSink):
    """SIEM sink for Elastic Cloud."""

    def _get_basic_auth_header(self, username, password):
        """Base64 encodes the username and password for basic authentication."""
        return f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"

    def create_sink(self):
        """Creates a Kinesis Firehose to deliver data to Elastic Cloud."""
        # 1. Get Elastic config from SSM
        endpoint = ssm.StringParameter.from_secure_string_parameter_name(
            self.scope, "ElasticEndpoint", parameter_name="/sec/elastic/endpoint"
        ).string_value
        username = ssm.StringParameter.from_secure_string_parameter_name(
            self.scope, "ElasticUsername", parameter_name="/sec/elastic/username"
        ).string_value
        password = ssm.StringParameter.from_secure_string_parameter_name(
            self.scope, "ElasticPassword", parameter_name="/sec/elastic/password"
        ).string_value

        # 2. Create backup bucket and Firehose role
        backup_bucket = self._create_backup_bucket()
        firehose_role = self._create_firehose_role("Elastic", backup_bucket)

        # 3. Create Kinesis Firehose Delivery Stream
        delivery_stream = firehose.CfnDeliveryStream(
            self.scope,
            "ElasticDeliveryStream",
            delivery_stream_type="DirectPut",
            http_endpoint_destination_configuration=firehose.CfnDeliveryStream.HttpEndpointDestinationConfigurationProperty(
                endpoint_configuration=firehose.CfnDeliveryStream.HttpEndpointConfigurationProperty(
                    url=endpoint,
                    name="Elastic Cloud Endpoint",
                    access_key=password,  # Using access_key for the password/token
                ),
                s3_backup_mode="FailedDataOnly",
                s3_configuration=firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                    bucket_arn=backup_bucket.bucket_arn,
                    role_arn=firehose_role.role_arn,
                    compression_format="GZIP",
                ),
                retry_options=firehose.CfnDeliveryStream.HttpEndpointRetryOptionsProperty(
                    duration_in_seconds=300
                ),
                request_configuration=firehose.CfnDeliveryStream.HttpEndpointRequestConfigurationProperty(
                    common_attributes=[
                        firehose.CfnDeliveryStream.HttpEndpointCommonAttributeProperty(
                            attribute_name="Authorization",
                            attribute_value=self._get_basic_auth_header(
                                username, password
                            ),
                        )
                    ]
                ),
            ),
        )

        # 4. Create CloudWatch Alarms
        self._create_cloudwatch_alarms(delivery_stream.ref, "Elastic")

        CfnOutput(self.scope, "ElasticDeliveryStreamName", value=delivery_stream.ref)


class SiemSinksFactory:
    """Factory for creating SIEM sinks."""

    def __init__(self, scope: Construct, security_lake_stack: SecurityLakeStack):
        self.scope = scope
        self.security_lake_stack = security_lake_stack

    def create_sink(self, sink_type: str) -> SiemSink:
        if sink_type == "opensearch":
            return OpenSearchSink(self.scope, "OpenSearch", self.security_lake_stack)
        elif sink_type == "splunk":
            return SplunkSink(self.scope, "Splunk", self.security_lake_stack)
        elif sink_type == "elastic":
            return ElasticSink(self.scope, "Elastic", self.security_lake_stack)
        else:
            raise ValueError(f"Unsupported SIEM sink type: {sink_type}")


class SiemSinksStack(Stack):
    """
    This stack defines the SIEM sinks for Security Lake.
    It includes a factory pattern for creating sinks to various destinations
    like Elastic, OpenSearch, and Splunk.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        security_lake_stack: SecurityLakeStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        sink_type = self.node.try_get_context("sinkType")
        if not sink_type:
            raise ValueError(
                "A 'sinkType' must be provided in the CDK context (e.g., 'opensearch', 'splunk', 'elastic')."
            )

        factory = SiemSinksFactory(self, security_lake_stack)
        sink = factory.create_sink(sink_type)
        sink.create_sink()

        Tags.of(self).add("Project", "Ecommerce")
        Tags.of(self).add("Stack", "SiemSinks")
