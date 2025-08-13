from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_guardduty as guardduty,
    aws_securityhub as securityhub,
    aws_config as config,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    CfnOutput,
    Duration,
    Tags,
    CfnResource,
)
from constructs import Construct


class SecurityBaselineStack(Stack):
    """
    This stack establishes the security baseline for the organization.
    It includes configurations for GuardDuty, Security Hub, Detective, and AWS Config.
    """

    def __init__(
        self, scope: Construct, construct_id: str, security_admin_email: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the security admin account ID from context
        org_delegated_admin_account_id = self.node.try_get_context(
            "orgDelegatedAdminAccountId"
        )
        if not org_delegated_admin_account_id:
            raise ValueError(
                "Organization delegated admin account ID must be provided in context"
            )

        security_account_id = self.node.try_get_context("securityAccountId")
        if not security_account_id:
            raise ValueError("Security account ID must be provided in context")

        enable_eks_audit = self.node.try_get_context("enableEksAudit")

        # Create a delegated admin role for the security account
        delegated_admin_role = iam.Role(
            self,
            "DelegatedAdminRole",
            assumed_by=iam.AccountPrincipal(org_delegated_admin_account_id),
            role_name="SecurityBaselineDelegatedAdminRole",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSSecurityHubFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonGuardDutyFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDetectiveFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSConfig_FullAccess"),
            ],
        )

        # Enable GuardDuty with organization-wide coverage
        guardduty_detector = guardduty.CfnDetector(
            self,
            "GuardDutyDetector",
            enable=True,
            finding_publishing_frequency="FIFTEEN_MINUTES",
            data_sources=guardduty.CfnDetector.DataSourcesProperty(
                s3_logs=guardduty.CfnDetector.S3LogsConfigurationProperty(enable=True),
                kubernetes=guardduty.CfnDetector.KubernetesConfigurationProperty(
                    audit_logs=guardduty.CfnDetector.KubernetesAuditLogsConfigurationProperty(
                        enable=enable_eks_audit
                    )
                ),
            ),
        )

        guardduty.CfnMember(
            self,
            "GuardDutyMember",
            detector_id=guardduty_detector.ref,
            email=security_admin_email,
            member_id=security_account_id,
            status="Invited",
        )

        # Enable Security Hub with CIS and Foundational standards
        security_hub = securityhub.CfnHub(
            self,
            "SecurityHub",
            enable_default_standards=False,
            control_finding_generator="STANDARD_CONTROL",
        )

        securityhub.CfnStandard(
            self,
            "CISStandard",
            hub_arn=security_hub.attr_arn,
            standards_arn="arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0",
        )

        securityhub.CfnStandard(
            self,
            "FoundationalStandard",
            hub_arn=security_hub.attr_arn,
            standards_arn="arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0",
        )

        # Enable Detective for security investigation
        detective_graph = CfnResource(
            self, "DetectiveGraph", type="AWS::Detective::Graph"
        )

        # Enable AWS Config with conformance packs
        config_recorder = config.CfnConfigurationRecorder(
            self,
            "ConfigRecorder",
            role_arn=delegated_admin_role.role_arn,
            recording_group=config.CfnConfigurationRecorder.RecordingGroupProperty(
                all_supported=True, include_global_resource_types=True
            ),
        )

        config.CfnDeliveryChannel(
            self,
            "ConfigDeliveryChannel",
            s3_bucket_name=f"config-bucket-{self.account}",
            config_snapshot_delivery_properties=config.CfnDeliveryChannel.ConfigSnapshotDeliveryPropertiesProperty(
                delivery_frequency="TwentyFour_Hours"
            ),
        )

        # CloudWatch alarms for security findings
        security_topic = sns.Topic(self, "SecurityFindingsTopic")
        security_topic.add_subscription(
            subscriptions.EmailSubscription(security_admin_email)
        )

        cloudwatch.Alarm(
            self,
            "HighSeverityGuardDutyFindings",
            metric=cloudwatch.Metric(
                namespace="AWS/GuardDuty",
                metric_name="HighSeverityFindings",
                dimensions_map={"DetectorId": guardduty_detector.ref},
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm for high severity GuardDuty findings",
            actions_enabled=True,
        ).add_alarm_action(cloudwatch_actions.SnsAction(security_topic))

        cloudwatch.Alarm(
            self,
            "CriticalSecurityHubFindings",
            metric=cloudwatch.Metric(
                namespace="AWS/SecurityHub",
                metric_name="CriticalFindings",
                dimensions_map={"HubArn": security_hub.attr_arn},
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm for critical severity Security Hub findings",
            actions_enabled=True,
        ).add_alarm_action(cloudwatch_actions.SnsAction(security_topic))

        # Add tags to all resources in the stack
        Tags.of(self).add("Project", "Ecommerce")
        Tags.of(self).add("Stack", "SecurityBaseline")

        # Outputs
        CfnOutput(self, "DelegatedAdminRoleArn", value=delegated_admin_role.role_arn)
        CfnOutput(self, "GuardDutyDetectorId", value=guardduty_detector.ref)
        CfnOutput(self, "SecurityHubArn", value=security_hub.attr_arn)
