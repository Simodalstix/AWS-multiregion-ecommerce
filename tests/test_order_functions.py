import json
import os
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.functions.order.create_order import handler as create_handler
from src.functions.order.get_order import handler as get_handler

# Mock AWS services
@pytest.fixture
def mock_dynamodb():
    with patch('boto3.resource') as mock_resource:
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table

@pytest.fixture
def mock_events():
    with patch('boto3.client') as mock_client:
        yield mock_client.return_value

# Test data
sample_order = {
    'customerId': 'test-customer-1',
    'items': [
        {'id': 'item1', 'quantity': 2, 'price': 10.99},
        {'id': 'item2', 'quantity': 1, 'price': 29.99}
    ]
}

@pytest.fixture
def mock_env():
    os.environ['ORDERS_TABLE'] = 'test-orders-table'
    os.environ['EVENT_BUS_ARN'] = 'arn:aws:events:region:account:event-bus/test-bus'
    yield
    del os.environ['ORDERS_TABLE']
    del os.environ['EVENT_BUS_ARN']

def test_create_order_success(mock_dynamodb, mock_events, mock_env):
    # Arrange
    mock_dynamodb.put_item.return_value = {}
    mock_events.put_events.return_value = {'FailedEntryCount': 0}
    
    event = {
        'body': json.dumps(sample_order)
    }

    # Act
    response = create_handler(event, None)

    # Assert
    assert response['statusCode'] == 200
    order_data = json.loads(response['body'])
    assert order_data['customerId'] == sample_order['customerId']
    assert order_data['status'] == 'PENDING'
    assert 'orderId' in order_data
    assert 'timestamp' in order_data
    
    # Verify DynamoDB and EventBridge calls
    mock_dynamodb.put_item.assert_called_once()
    mock_events.put_events.assert_called_once()

def test_create_order_missing_fields(mock_dynamodb, mock_events, mock_env):
    # Arrange
    invalid_order = {'customerId': 'test-customer-1'}  # Missing items
    event = {
        'body': json.dumps(invalid_order)
    }

    # Act
    response = create_handler(event, None)

    # Assert
    assert response['statusCode'] == 400
    error = json.loads(response['body'])
    assert 'error' in error
    assert 'Missing required fields' in error['error']

def test_get_order_success(mock_dynamodb, mock_env):
    # Arrange
    mock_order = {
        'orderId': 'test-order-1',
        'customerId': 'test-customer-1',
        'status': 'PENDING'
    }
    mock_dynamodb.get_item.return_value = {'Item': mock_order}
    
    event = {
        'pathParameters': {'orderId': 'test-order-1'}
    }

    # Act
    response = get_handler(event, None)

    # Assert
    assert response['statusCode'] == 200
    order_data = json.loads(response['body'])
    assert order_data['orderId'] == mock_order['orderId']
    assert order_data['customerId'] == mock_order['customerId']

def test_get_order_not_found(mock_dynamodb, mock_env):
    # Arrange
    mock_dynamodb.get_item.return_value = {}
    
    event = {
        'pathParameters': {'orderId': 'non-existent-order'}
    }

    # Act
    response = get_handler(event, None)

    # Assert
    assert response['statusCode'] == 404
    error = json.loads(response['body'])
    assert 'error' in error
    assert 'Order not found' in error['error']

def test_get_order_missing_id(mock_dynamodb, mock_env):
    # Arrange
    event = {
        'pathParameters': {}  # Missing orderId
    }

    # Act
    response = get_handler(event, None)

    # Assert
    assert response['statusCode'] == 400
    error = json.loads(response['body'])
    assert 'error' in error
    assert 'Missing orderId' in error['error']