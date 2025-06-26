from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_route53 as route53,
    CfnOutput,
    RemovalPolicy,
    Tags
)
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC in primary region
        self.vpc = ec2.Vpc(
            self, "EcommerceVPC",
            max_azs=3,
            nat_gateways=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # Add VPC Flow Logs
        self.vpc.add_flow_log("FlowLogs",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(),
            traffic_type=ec2.FlowLogTrafficType.ALL
        )

        # Create Route53 private hosted zone
        self.private_zone = route53.PrivateHostedZone(
            self, "PrivateZone",
            vpc=self.vpc,
            zone_name="ecommerce.internal"
        )

        # Add tags
        Tags.of(self).add("Project", "Ecommerce")
        Tags.of(self).add("Environment", "Production")

        # Outputs
        CfnOutput(
            self, "VPCId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.stack_name}-VPCId"
        )

        CfnOutput(
            self, "PrivateHostedZoneId",
            value=self.private_zone.hosted_zone_id,
            description="Private Hosted Zone ID",
            export_name=f"{self.stack_name}-PrivateHostedZoneId"
        )