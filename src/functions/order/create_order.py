import json
import os
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    dynamodb = boto3.resource("dynamodb")
    events = boto3.client("events")
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    event_bus_arn = os.environ["EVENT_BUS_ARN"]
    """Lambda handler for creating orders"""
    try:
        # Parse request body
        body = json.loads(event["body"], parse_float=Decimal)

        # Validate request
        if not body.get("customerId") or not body.get("items"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"}),
            }

        # Create order
        order = create_order_record(body)

        # Publish event
        publish_order_event(order, "OrderCreated")

        return {"statusCode": 200, "body": json.dumps(order, default=str)}

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON"}),
        }
    except Exception as e:
        print(f"Error processing order: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
