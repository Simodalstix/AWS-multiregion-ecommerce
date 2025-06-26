#!/usr/bin/env python3
import os
import aws_cdk as cdk
from infrastructure.lib.pipeline_stack import PipelineStack

app = cdk.App()

# Environment configurations
primary_env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "ap-southeast-2"),  # Primary region
)

# CI/CD Pipeline stack (deployed in primary region)
pipeline = PipelineStack(
    app,
    "PipelineStack",
    env=primary_env,
    description="CI/CD pipeline for multi-region deployment",
)

# Tags for pipeline stack
cdk.Tags.of(pipeline).add("Project", "Ecommerce")
cdk.Tags.of(pipeline).add("Environment", "Production")

app.synth()
