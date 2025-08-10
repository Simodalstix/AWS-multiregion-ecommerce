#!/usr/bin/env python3
import os
import aws_cdk as cdk
from infrastructure.lib.network_stack import NetworkStack
from infrastructure.lib.core_services_stack import CoreServicesStack
from infrastructure.lib.api_compute_stack import ApiComputeStack
from infrastructure.lib.security.security_baseline_stack import SecurityBaselineStack
from infrastructure.lib.security.security_lake_stack import SecurityLakeStack
from infrastructure.lib.security.siem_sinks_stack import SiemSinksStack

app = cdk.App()

# Environment configurations
primary_env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "ap-southeast-2"),  # Primary region
)

secondary_env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region="us-west-2",  # Secondary region (US West)
)

# Primary region stacks
security_baseline = SecurityBaselineStack(
    app,
    "SecurityBaselineStack",
    env=primary_env,
    description="Security baseline for the organization",
    security_admin_email=app.node.try_get_context("security_admin_email"),
)

security_lake = SecurityLakeStack(
    app,
    "SecurityLakeStack",
    env=primary_env,
    primary_region=primary_env.region,
    secondary_region=secondary_env.region,
    security_admin_account_id=app.node.try_get_context("security_admin_account_id"),
    description="Security Lake for centralized security data",
)

siem_sinks = SiemSinksStack(
    app,
    "SiemSinksStack",
    env=primary_env,
    security_lake_stack=security_lake,
    description="SIEM sinks for Security Lake",
)

primary_network = NetworkStack(
    app,
    "PrimaryNetworkStack",
    env=primary_env,
    description="Network infrastructure for primary region",
)

primary_core = CoreServicesStack(
    app,
    "PrimaryCoreStack",
    env=primary_env,
    description="Core services for primary region",
)

primary_api = ApiComputeStack(
    app,
    "PrimaryApiStack",
    event_bus_arn=primary_core.event_bus.event_bus_arn,
    orders_table_name=primary_core.orders_table.table_name,
    vpc=primary_network.vpc,
    env=primary_env,
    description="API and compute resources for primary region",
)

# Secondary region stacks
secondary_network = NetworkStack(
    app,
    "SecondaryNetworkStack",
    env=secondary_env,
    description="Network infrastructure for secondary region",
)

secondary_core = CoreServicesStack(
    app,
    "SecondaryCoreStack",
    env=secondary_env,
    description="Core services for secondary region",
)

secondary_api = ApiComputeStack(
    app,
    "SecondaryApiStack",
    event_bus_arn=secondary_core.event_bus.event_bus_arn,
    orders_table_name=secondary_core.orders_table.table_name,
    vpc=secondary_network.vpc,
    env=secondary_env,
    description="API and compute resources for secondary region",
)

# Add dependencies
primary_core.add_dependency(primary_network)
primary_api.add_dependency(primary_core)
secondary_core.add_dependency(secondary_network)
secondary_api.add_dependency(secondary_core)
siem_sinks.add_dependency(security_lake)
security_lake.add_dependency(security_baseline)

# Tags for all stacks
for stack in [
    primary_network,
    primary_core,
    primary_api,
    secondary_network,
    secondary_core,
    secondary_api,
    security_baseline,
    security_lake,
    siem_sinks,
]:
    cdk.Tags.of(stack).add("Project", "Ecommerce")
    cdk.Tags.of(stack).add("Environment", "Production")

app.synth()
