import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from infrastructure.lib.security.security_lake_stack import SecurityLakeStack


class TestSecurityLakeStack:
    """Test suite for the SecurityLakeStack."""

    def test_security_lake_created_with_correct_config(self):
        """Test that Security Lake is created with correct configuration."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check that the Security Lake data lake is created
        template.has_resource_properties(
            "AWS::SecurityLake::DataLake", {"Configuration": {"Region": "us-east-1"}}
        )

    def test_delegated_admin_configured(self):
        """Test that delegated admin is configured correctly."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::SecurityLake::DelegatedAdmin", {"AccountId": "111111111111"}
        )

    def test_data_sources_enabled(self):
        """Test that all required data sources are enabled."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check CloudTrail data source
        template.has_resource_properties(
            "AWS::SecurityLake::AwsLogSource",
            {"SourceName": "CLOUD_TRAIL_MGMT_AND_DATA_EVENTS", "SourceVersion": "1.0"},
        )

        # Check VPC Flow Logs data source
        template.has_resource_properties(
            "AWS::SecurityLake::AwsLogSource",
            {"SourceName": "VPC_FLOW_LOGS", "SourceVersion": "1.0"},
        )

        # Check Route 53 Resolver query logs data source
        template.has_resource_properties(
            "AWS::SecurityLake::AwsLogSource",
            {"SourceName": "ROUTE53_RESOLVER_QUERY_LOGS", "SourceVersion": "1.0"},
        )

        # Check S3 server access logs data source
        template.has_resource_properties(
            "AWS::SecurityLake::AwsLogSource",
            {"SourceName": "S3_SERVER_ACCESS_LOGS", "SourceVersion": "1.0"},
        )

    def test_eks_audit_flag_logic(self):
        """Test the EKS audit flag logic."""
        # Given
        app = App(context={"enableEksAudit": True})
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check EKS audit logs data source is enabled when flag is True
        template.has_resource_properties(
            "AWS::SecurityLake::AwsLogSource",
            {"SourceName": "EKS_AUDIT_LOGS", "SourceVersion": "1.0"},
        )

    def test_data_lake_bucket_configured(self):
        """Test that the S3 data lake bucket is configured correctly."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check that the bucket is created with correct properties
        template.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "BucketName": {
                    "Fn::Join": [
                        "",
                        [
                            "aws-security-lake-bucket-",
                            {"Ref": "AWS::AccountId"},
                            "-",
                            {"Ref": "AWS::Region"},
                        ],
                    ]
                }
            },
        )

        # Check that the bucket has encryption enabled
        template.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "BucketEncryption": {
                    "ServerSideEncryptionConfiguration": [
                        {
                            "ServerSideEncryptionByDefault": {
                                "KMSMasterKeyID": {
                                    "Fn::GetAtt": ["SecurityLakeKmsKey6E20204F", "Arn"]
                                },
                                "SSEAlgorithm": "aws:kms",
                            }
                        }
                    ]
                }
            },
        )

    def test_glue_catalog_resources_created(self):
        """Test that Glue catalog resources are created correctly."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        # Check that the Glue database is created
        template.has_resource_properties(
            "AWS::Glue::Database",
            {
                "DatabaseInput": {
                    "Name": "security_lake_db",
                    "Description": "Database for Security Lake OCSF data",
                }
            },
        )

        # Check that the Glue table is created
        template.has_resource_properties(
            "AWS::Glue::Table",
            {
                "DatabaseName": {"Ref": "SecurityLakeGlueDatabase"},
                "TableInput": {
                    "Name": "ocsf_table",
                    "Description": "Table for OCSF schema in Security Lake",
                    "TableType": "EXTERNAL_TABLE",
                },
            },
        )

    def test_subscriber_role_created(self):
        """Test that the subscriber role is created with correct permissions."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::IAM::Role", {"RoleName": "SecurityLakeSubscriberRole"}
        )

        # Check that the role can be assumed by the security admin account
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":iam::111111111111:root",
                                        ],
                                    ]
                                }
                            },
                        }
                    ]
                }
            },
        )

    def test_kms_key_created(self):
        """Test that the KMS key is created with correct configuration."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_resource_properties(
            "AWS::KMS::Key",
            {
                "Description": "KMS key for Security Lake encryption",
                "EnableKeyRotation": True,
            },
        )

        # Check that the key has an alias
        template.has_resource_properties(
            "AWS::KMS::Alias", {"AliasName": "alias/security-lake-key"}
        )

    def test_outputs_created(self):
        """Test that stack outputs are created."""
        # Given
        app = App()
        stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        template = Template.from_stack(stack)

        # Then
        template.has_output("SecurityLakeBucketName", {})
        template.has_output("SecurityLakeGlueDatabaseName", {})
        template.has_output("SubscriberRoleArn", {})
