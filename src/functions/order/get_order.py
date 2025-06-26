import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from typing import Dict, Any
from botocore.exceptions import ClientError


dynamodb = None


def get_order_by_id(order_id: str) -> Dict[str, Any]:
    """Retrieve an order from DynamoDB by order ID"""
    global dynamodb
    if dynamodb is None:
        dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    try:
        # Since we have a composite key (orderId + timestamp), we need to query
        # instead of get_item when we only know the partition key
        response = table.query(
            KeyConditionExpression=Key('orderId').eq(order_id)
        )
        items = response.get('Items', [])
        # Return the first (and should be only) item since orderId should be unique
        return items[0] if items else None
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
