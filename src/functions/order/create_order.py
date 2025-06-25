import json
import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')
table = dynamodb.Table(os.environ['ORDERS_TABLE'])
event_bus_arn = os.environ['EVENT_BUS_ARN']

def create_order_record(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new order record in DynamoDB"""
    timestamp = datetime.utcnow().isoformat()
    order_id = str(uuid.uuid4())
    
    item = {
        'orderId': order_id,
        'timestamp': timestamp,
        'customerId': order_data['customerId'],
        'items': order_data['items'],
        'totalAmount': sum(item['price'] * item['quantity'] for item in order_data['items']),
        'status': 'PENDING',
        'ttl': int((datetime.now().timestamp() + (90 * 24 * 60 * 60)))  # 90 days TTL
    }
    
    table.put_item(Item=item)
    return item

def publish_order_event(order: Dict[str, Any], event_type: str) -> None:
    """Publish order event to EventBridge"""
    events.put_events(
        Entries=[{
            'Source': 'ecommerce.orders',
            'DetailType': event_type,
            'Detail': json.dumps(order),
            'EventBusName': event_bus_arn.split('/')[-1]
        }]
    )

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for creating orders"""
    try:
        # Parse request body
        body = json.loads(event['body'])
        
        # Validate request
        if not body.get('customerId') or not body.get('items'):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: customerId and items'
                })
            }
        
        # Create order
        order = create_order_record(body)
        
        # Publish event
        publish_order_event(order, 'OrderCreated')
        
        return {
            'statusCode': 200,
            'body': json.dumps(order)
        }
        
    except Exception as e:
        print(f"Error processing order: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }