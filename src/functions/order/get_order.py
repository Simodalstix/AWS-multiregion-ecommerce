import json
import os
import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ORDERS_TABLE"])


def get_order_by_id(order_id: str) -> Dict[str, Any] | None:
    """Retrieve an order from DynamoDB by order ID"""
    try:
        response = table.get_item(Key={"orderId": order_id})
        return response.get("Item")
    except ClientError as e:
        print(f"Error retrieving order: {str(e)}")
        return None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for retrieving orders"""
    try:
        # Get order ID from path parameters
        order_id = event["pathParameters"]["orderId"]

        # Retrieve order
        order = get_order_by_id(order_id)

        if not order:
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}

        return {"statusCode": 200, "body": json.dumps(order, default=str)}

    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing orderId parameter"}),
        }
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
