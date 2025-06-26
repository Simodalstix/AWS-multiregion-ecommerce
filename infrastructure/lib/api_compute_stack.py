from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    Duration,
    CfnOutput
)
from constructs import Construct

class ApiComputeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 event_bus_arn: str, orders_table_name: str, 
                 vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda execution role with permissions
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add permissions for DynamoDB and EventBridge
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                resources=[f"arn:aws:dynamodb:*:*:table/{orders_table_name}*"]
            )
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[event_bus_arn]
            )
        )

        # Create Lambda functions for order processing
        create_order_fn = lambda_.Function(
            self, "CreateOrderFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="create_order.handler",
            code=lambda_.Code.from_asset("src/functions/order"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            vpc=vpc,
            environment={
                "ORDERS_TABLE": orders_table_name,
                "EVENT_BUS_ARN": event_bus_arn
            }
        )

        get_order_fn = lambda_.Function(
            self, "GetOrderFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="get_order.handler",
            code=lambda_.Code.from_asset("src/functions/order"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            vpc=vpc,
            environment={
                "ORDERS_TABLE": orders_table_name
            }
        )

        # Create API Gateway
        api = apigateway.RestApi(
            self, "EcommerceApi",
            rest_api_name="Ecommerce Service",
            description="API for e-commerce order processing",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
                tracing_enabled=True
            )
        )

        # Add API resources and methods
        orders = api.root.add_resource("orders")
        
        # POST /orders
        orders.add_method(
            "POST",
            apigateway.LambdaIntegration(
                create_order_fn,
                proxy=True,
                integration_responses=[{
                    "statusCode": "200",
                    "responseParameters": {
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                }]
            ),
            method_responses=[{
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Origin": True
                }
            }]
        )

        # GET /orders/{orderId}
        order = orders.add_resource("{orderId}")
        order.add_method(
            "GET",
            apigateway.LambdaIntegration(
                get_order_fn,
                proxy=True,
                integration_responses=[{
                    "statusCode": "200",
                    "responseParameters": {
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                }]
            ),
            method_responses=[{
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Origin": True
                }
            }]
        )

        # Enable CORS
        orders.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
        )

        # Outputs
        CfnOutput(
            self, "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint",
            export_name=f"{self.stack_name}-ApiEndpoint"
        )