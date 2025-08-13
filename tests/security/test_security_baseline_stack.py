import json
import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from infrastructure.lib.security.security_baseline_stack import SecurityBaselineStack


class TestSecurityBaselineStack:
    """Test suite for the SecurityBaselineStack."""

    def test_guardduty_enabled(self):
        """Test that GuardDuty is enabled with correct configuration."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::GuardDuty::Detector",
            {"Enable": True, "FindingPublishingFrequency": "FIFTEEN_MINUTES"},
        )

    def test_security_hub_enabled_with_standards(self):
        """Test that Security Hub is enabled with required standards."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::SecurityHub::Hub", {"ControlFindingGenerator": "STANDARD_CONTROL"}
        )

        # Check that standards are enabled
        template.has_resource_properties(
            "AWS::SecurityHub::Standard",
            {
                "StandardsArn": "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"
            },
        )

        template.has_resource_properties(
            "AWS::SecurityHub::Standard",
            {
                "StandardsArn": "arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"
            },
        )

    def test_detective_enabled(self):
        """Test that Detective is enabled."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties("AWS::Detective::Graph", {})

    def test_config_recorder_configured(self):
        """Test that AWS Config recorder is configured."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::Config::ConfigurationRecorder",
            {
                "RecordingGroup": {
                    "AllSupported": True,
                    "IncludeGlobalResourceTypes": True,
                }
            },
        )

    def test_delegated_admin_role_created(self):
        """Test that the delegated admin role is created with correct policies."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::IAM::Role", {"RoleName": "SecurityBaselineDelegatedAdminRole"}
        )

        # Check that the role has the required managed policies
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "ManagedPolicyArns": [
                    {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":iam::aws:policy/AWSSecurityHubFullAccess",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":iam::aws:policy/AmazonGuardDutyFullAccess",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":iam::aws:policy/AmazonDetectiveFullAccess",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":iam::aws:policy/AWSConfig_FullAccess",
                            ],
                        ]
                    },
                ]
            },
        )

    def test_cloudwatch_alarms_created(self):
        """Test that CloudWatch alarms are created for security findings."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check high severity GuardDuty findings alarm
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {
                "AlarmDescription": "Alarm for high severity GuardDuty findings",
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                "MetricName": "HighSeverityFindings",
                "Namespace": "AWS/GuardDuty",
            },
        )

        # Check critical Security Hub findings alarm
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {
                "AlarmDescription": "Alarm for critical severity Security Hub findings",
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                "MetricName": "CriticalFindings",
                "Namespace": "AWS/SecurityHub",
            },
        )

    def test_outputs_created(self):
        """Test that stack outputs are created."""
        # Given
        app = App()
        stack = SecurityBaselineStack(
            app,
            "test-security-baseline",
            security_admin_email="test@example.com",
            env=Environment(account="123456789012", region="us-east-1"),
            orgDelegatedAdminAccountId="111111111111",
            securityAccountId="222222222222",
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_output("DelegatedAdminRoleArn", {})
        template.has_output("GuardDutyDetectorId", {})
        template.has_output("SecurityHubArn", {})
