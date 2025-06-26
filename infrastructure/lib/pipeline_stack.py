from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as pipeline_actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_s3 as s3,
    SecretValue,
    Duration,
    CfnOutput
)
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create artifact bucket
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(30),
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                )
            ]
        )

        # Create a separate CodeBuild project for running tests
        test_project = codebuild.Project(
            self, "TestProject",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.11"
                        },
                        "commands": [
                            "pip install -r requirements.txt",
                            "pip install -r requirements-dev.txt",
                            "pip install -e ."
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Running tests...",
                            "export ORDERS_TABLE=test-orders-table",
                            "export EVENT_BUS_ARN=arn:aws:events:region:account:event-bus/test-bus",
                            "python -m pytest tests/ -vv",
                            "unset ORDERS_TABLE EVENT_BUS_ARN"
                        ]
                    }
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            )
        )

        # Create CodeBuild project for CDK synthesis
        build_project = codebuild.PipelineProject(
            self, "CDKBuild",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.11",
                            "nodejs": "18"
                        },
                        "commands": [
                            "npm install -g aws-cdk",
                            "pip install -r requirements.txt"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Synthesizing CDK app...",
                            "cdk synth"
                        ]
                    }
                },
                "artifacts": {
                    "files": [
                        "cdk.out/**/*"
                    ]
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            )
        )

        # Create Pipeline
        pipeline = codepipeline.Pipeline(
            self, "DeploymentPipeline",
            artifact_bucket=artifact_bucket,
            cross_account_keys=True,
            restart_execution_on_update=True
        )

        # Source stage
        source_output = codepipeline.Artifact()
        source_action = pipeline_actions.GitHubSourceAction(
            action_name="GitHub",
            owner="Simodalstix",
            repo="AWS-multiregion-ecommerce",
            branch="main",
            oauth_token=SecretValue.secrets_manager("github-token"),
            output=source_output,
            trigger=pipeline_actions.GitHubTrigger.WEBHOOK
        )
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Build stage
        build_output = codepipeline.Artifact("BuildOutput")
        build_action = pipeline_actions.CodeBuildAction(
            action_name="CDKBuild",
            project=build_project,
            input=source_output,
            outputs=[build_output],
            run_order=1
        )
        test_action = pipeline_actions.CodeBuildAction(
            action_name="Test",
            project=test_project,
            input=source_output,
            run_order=1
        )

        pipeline.add_stage(
            stage_name="Test",
            actions=[test_action]
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[build_action],
        )

        # Deploy to primary region
        deploy_primary = pipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name="Deploy_Primary_Region",
            stack_name="EcommercePrimary",
            template_path=build_output.at_path("cdk.out/EcommercePrimary.template.json"),
            admin_permissions=True,
            run_order=1
        )

        # Deploy to secondary region
        deploy_secondary = pipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name="Deploy_Secondary_Region",
            stack_name="EcommerceSecondary",
            template_path=build_output.at_path("cdk.out/EcommerceSecondary.template.json"),
            admin_permissions=True,
            region="ap-southeast-2",  # Secondary region
            run_order=2
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[deploy_primary, deploy_secondary]
        )

        # Outputs
        CfnOutput(
            self, "PipelineArn",
            value=pipeline.pipeline_arn,
            description="CodePipeline ARN",
            export_name=f"{self.stack_name}-PipelineArn"
        )

        CfnOutput(
            self, "ArtifactBucketName",
            value=artifact_bucket.bucket_name,
            description="Pipeline Artifact Bucket",
            export_name=f"{self.stack_name}-ArtifactBucket"
        )