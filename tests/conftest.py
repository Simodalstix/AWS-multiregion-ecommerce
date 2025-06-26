import os
import pytest
from unittest.mock import Mock, patch

# Set environment variables before any imports
os.environ['ORDERS_TABLE'] = 'test-orders-table'
os.environ['EVENT_BUS_ARN'] = 'arn:aws:events:ap-southeast-2:123456789012:event-bus/test-event-bus'

# Mock boto3 at the session level
@pytest.fixture(scope="session", autouse=True)
def mock_boto3():
    with patch('boto3.resource') as mock_resource, \
         patch('boto3.client') as mock_client:
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        # Mock EventBridge client
        mock_events = Mock()
        mock_events.put_events.return_value = {'FailedEntryCount': 0}
        mock_client.return_value = mock_events
        
        yield {
            'table': mock_table,
            'events': mock_events,
            'dynamodb': mock_dynamodb
        }