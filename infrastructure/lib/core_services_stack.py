from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct

class CoreServicesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB Global Table for Orders
        self.orders_table = dynamodb.Table(
            self, "OrdersTable",
            partition_key=dynamodb.Attribute(
                name="orderId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            replication_regions=[region for region in ["us-west-2", "ap-southeast-2"] if region != Stack.of(self).region],
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"
        )

        # Add GSIs for querying
        self.orders_table.add_global_secondary_index(
            index_name="CustomerOrders",
            partition_key=dynamodb.Attribute(
                name="customerId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            )
        )

        self.orders_table.add_global_secondary_index(
            index_name="OrderStatus",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Create EventBridge Event Bus
        self.event_bus = events.EventBus(
            self, "EcommerceEventBus",
            event_bus_name="ecommerce-events"
        )

        # Create rule for order events
        events.Rule(
            self, "OrderEventsRule",
            event_bus=self.event_bus,
            description="Handle order processing events",
            event_pattern=events.EventPattern(
                source=["ecommerce.orders"]
            )
        )

        # Create event archive
        self.event_bus.archive(
            "EventArchive",
            archive_name="ecommerce-events-archive",
            description="Archive of all ecommerce events",
            retention=Duration.days(365),
            event_pattern=events.EventPattern(
                source=["ecommerce.orders"]
            )
        )

        # Outputs
        CfnOutput(
            self, "OrdersTableName",
            value=self.orders_table.table_name,
            description="DynamoDB Orders Table Name",
            export_name=f"{self.stack_name}-OrdersTableName"
        )

        CfnOutput(
            self, "EventBusArn",
            value=self.event_bus.event_bus_arn,
            description="EventBridge Event Bus ARN",
            export_name=f"{self.stack_name}-EventBusArn"
        )