import json
from unittest.mock import patch
import pytest
from src.functions.order.create_order import handler as create_handler
from src.functions.order.get_order import handler as get_handler

# Test data
sample_order = {
    "customerId": "test-customer-1",
    "items": [
        {"id": "item1", "quantity": 2, "price": 10.99},
        {"id": "item2", "quantity": 1, "price": 29.99},
    ],
}


def test_create_order_success(mock_boto3):
    # Arrange
    mock_table = mock_boto3["table"]
    mock_events = mock_boto3["events"]
    mock_table.put_item.return_value = {}
    mock_events.put_events.return_value = {"FailedEntryCount": 0}

    event = {"body": json.dumps(sample_order)}

    # Act
    response = create_handler(event, None)

    # Assert
    assert response["statusCode"] == 200
    order_data = json.loads(response["body"])
    assert order_data["customerId"] == sample_order["customerId"]
    assert order_data["status"] == "PENDING"
    assert "orderId" in order_data
    assert "timestamp" in order_data

    # Verify DynamoDB and EventBridge calls
    mock_table.put_item.assert_called_once()
    mock_events.put_events.assert_called_once()


def test_create_order_missing_fields():
    # Arrange
    event = {"body": json.dumps({"customerId": "test-customer-1"})}  # Missing items

    # Act
    response = create_handler(event, None)

    # Assert
    assert response["statusCode"] == 400
    error_data = json.loads(response["body"])
    assert "error" in error_data
    assert "Missing required fields" in error_data["error"]


def test_create_order_invalid_json():
    # Arrange
    event = {"body": "invalid json"}

    # Act
    response = create_handler(event, None)

    # Assert
    assert response["statusCode"] == 400
    error_data = json.loads(response["body"])
    assert "error" in error_data
    assert "Invalid JSON" in error_data["error"]


def test_get_order_success(mock_boto3):
    # Arrange
    mock_table = mock_boto3["table"]
    mock_order = {
        "orderId": "test-order-1",
        "customerId": "test-customer-1",
        "status": "PENDING",
    }
    mock_table.get_item.return_value = {"Item": mock_order}

    event = {"pathParameters": {"orderId": "test-order-1"}}

    # Act
    response = get_handler(event, None)

    # Assert
    assert response["statusCode"] == 200
    order_data = json.loads(response["body"])
    assert order_data["orderId"] == "test-order-1"
    assert order_data["customerId"] == "test-customer-1"
    assert order_data["status"] == "PENDING"

    # Verify DynamoDB call
    mock_table.get_item.assert_called_once_with(Key={"orderId": "test-order-1"})


def test_get_order_not_found(mock_boto3):
    # Arrange
    mock_table = mock_boto3["table"]
    mock_table.get_item.return_value = {}

    event = {"pathParameters": {"orderId": "non-existent-order"}}

    # Act
    response = get_handler(event, None)

    # Assert
    assert response["statusCode"] == 404
    error_data = json.loads(response["body"])
    assert "error" in error_data
    assert "Order not found" in error_data["error"]


def test_get_order_missing_parameter():
    # Arrange
    event = {"pathParameters": {}}  # Missing orderId

    # Act
    response = get_handler(event, None)

    # Assert
    assert response["statusCode"] == 400
    error_data = json.loads(response["body"])
    assert "error" in error_data
    assert "Missing orderId parameter" in error_data["error"]
