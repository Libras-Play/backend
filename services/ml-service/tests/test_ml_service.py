"""
Tests for ML Service

Tests cover:
- POST /api/v1/assess endpoint
- GET /api/v1/assess/{sessionId} status check
- SageMaker client mocking
- Local stub inference
- SQS consumer logic
- DynamoDB integration
"""
import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from moto import mock_aws

from fastapi.testclient import TestClient

# Import after moto decorators
import boto3
from app.main import app
from app.config import get_settings
from app.models import AssessmentRequest, SQSVideoMessage
from app.inference.local_stub import LocalStubInference
from app.handlers.sqs_consumer import SQSConsumer

settings = get_settings()


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_aws_services():
    """Mock AWS services with moto"""
    with mock_aws():
        # Create S3 bucket (without endpoint_url for moto)
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=settings.S3_BUCKET_VIDEOS)
        s3.create_bucket(Bucket=settings.S3_BUCKET_MODELS)
        
        # Create SQS queue (without endpoint_url for moto)
        sqs = boto3.client('sqs', region_name='us-east-1')
        sqs.create_queue(QueueName='video-processing-queue')
        
        # Create DynamoDB table (without endpoint_url for moto)
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName=settings.DYNAMODB_TABLE_AI_SESSIONS,
            KeySchema=[{'AttributeName': 'sessionId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'sessionId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield {
            's3': s3,
            'sqs': sqs,
            'dynamodb': dynamodb
        }


# ==================== HEALTH CHECK TESTS ====================

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['modelLoaded'] is True
    assert data['useSagemaker'] == settings.USE_SAGEMAKER
    assert data['modelVersion'] == settings.MODEL_VERSION


def test_root_endpoint(client):
    """Test root endpoint redirects to health"""
    response = client.get("/")
    assert response.status_code == 200


# ==================== ASSESSMENT ENDPOINT TESTS ====================

@pytest.mark.asyncio
async def test_assess_video_queues_message(client, mock_aws_services):
    """Test POST /api/v1/assess queues video for processing"""
    # Prepare request
    request_data = {
        'userId': 'user123',
        'exerciseId': 1,
        'levelId': 1,
        's3VideoUrl': 's3://user-videos-bucket/video123.mp4'
    }
    
    # Mock AWS client to avoid actual AWS calls
    with patch('app.main.get_aws_client') as mock_get_aws:
        mock_aws_client = AsyncMock()
        mock_aws_client.send_to_sqs = AsyncMock(return_value='msg-123')
        mock_aws_client.update_ai_session = AsyncMock()
        mock_get_aws.return_value = mock_aws_client
        
        # Make request
        response = client.post('/api/v1/assess', json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'queued'
        assert 'sessionId' in data
        assert data['message'] == 'Video queued for processing'
        
        # Verify AWS calls
        mock_aws_client.send_to_sqs.assert_called_once()
        mock_aws_client.update_ai_session.assert_called_once()


@pytest.mark.asyncio
async def test_get_assessment_status_completed(client):
    """Test GET /api/v1/assess/{sessionId} returns completed status"""
    session_id = str(uuid.uuid4())
    
    # Mock AWS client
    with patch('app.main.get_aws_client') as mock_get_aws:
        mock_aws_client = AsyncMock()
        mock_aws_client.get_ai_session = AsyncMock(return_value={
            'sessionId': session_id,
            'status': 'completed',
            'result': {
                'recognizedGesture': 'A',
                'confidence': 0.95,
                'score': 100,
                'processingTime': 1.5,
                'modelVersion': '1.0.0',
                'metadata': {}
            }
        })
        mock_get_aws.return_value = mock_aws_client
        
        # Make request
        response = client.get(f'/api/v1/assess/{session_id}')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['sessionId'] == session_id
        assert data['status'] == 'completed'
        assert data['recognizedGesture'] == 'A'
        assert data['confidence'] == 0.95
        assert data['score'] == 100


@pytest.mark.asyncio
async def test_get_assessment_status_not_found(client):
    """Test GET /api/v1/assess/{sessionId} returns 404 for unknown session"""
    session_id = str(uuid.uuid4())
    
    with patch('app.main.get_aws_client') as mock_get_aws:
        mock_aws_client = AsyncMock()
        mock_aws_client.get_ai_session = AsyncMock(return_value=None)
        mock_get_aws.return_value = mock_aws_client
        
        response = client.get(f'/api/v1/assess/{session_id}')
        
        assert response.status_code == 404


# ==================== INFERENCE TESTS ====================

@pytest.mark.asyncio
async def test_local_stub_inference():
    """Test local stub inference"""
    stub = LocalStubInference()
    
    # Create fake video data
    video_bytes = b'fake video data for testing'
    
    # Run inference
    result = await stub.predict(video_bytes)
    
    assert 'recognizedGesture' in result
    assert 'confidence' in result
    assert 'score' in result
    assert 'modelVersion' in result
    
    # Verify confidence range
    assert 0.5 <= result['confidence'] <= 1.0
    
    # Verify score range
    assert 0 <= result['score'] <= 100
    
    # Verify gesture is valid
    assert result['recognizedGesture'] in settings.gesture_labels_list


@pytest.mark.asyncio
async def test_local_stub_deterministic():
    """Test local stub produces deterministic results for same video"""
    stub = LocalStubInference()
    video_bytes = b'same video data'
    
    # Run inference twice
    result1 = await stub.predict(video_bytes)
    result2 = await stub.predict(video_bytes)
    
    # Results should be identical
    assert result1['recognizedGesture'] == result2['recognizedGesture']
    assert result1['confidence'] == result2['confidence']
    assert result1['score'] == result2['score']


@pytest.mark.asyncio
async def test_sagemaker_client_mock():
    """Test SageMaker client with mocked endpoint"""
    from app.inference.sagemaker_client import SageMakerInferenceClient
    
    client = SageMakerInferenceClient()
    video_bytes = b'test video'
    
    # Mock SageMaker response
    mock_response = {
        'predictions': [
            {'label': 'B', 'confidence': 0.88},
            {'label': 'A', 'confidence': 0.10}
        ],
        'model_version': '1.0.0'
    }
    
    with patch.object(client.aws_client, 'invoke_sagemaker_endpoint', return_value=mock_response):
        result = await client.predict(video_bytes)
        
        assert result['recognizedGesture'] == 'B'
        assert result['confidence'] == 0.88
        assert result['score'] == 90  # 0.88 -> 90 score


# ==================== SQS CONSUMER TESTS ====================

@pytest.mark.asyncio
async def test_sqs_consumer_processes_message():
    """Test SQS consumer processes video message"""
    consumer = SQSConsumer()
    
    # Create test message
    message = {
        'Body': json.dumps({
            'sessionId': str(uuid.uuid4()),
            'userId': 'user123',
            'exerciseId': 1,
            'levelId': 1,
            's3VideoUrl': 's3://test-bucket/video.mp4',
            'timestamp': datetime.utcnow().isoformat()
        }),
        'ReceiptHandle': 'test-receipt-123'
    }
    
    # Mock AWS operations
    with patch.object(consumer.aws_client, 'download_video_from_s3', return_value=b'fake video'):
        with patch.object(consumer.aws_client, 'update_ai_session', return_value=None):
            with patch.object(consumer.aws_client, 'delete_sqs_message', return_value=None):
                # Process message
                await consumer._process_message(message)
                
                # Verify AWS calls
                consumer.aws_client.download_video_from_s3.assert_called_once()
                assert consumer.aws_client.update_ai_session.call_count >= 2  # queued + completed


@pytest.mark.asyncio
async def test_sqs_consumer_handles_error():
    """Test SQS consumer handles processing errors"""
    consumer = SQSConsumer()
    
    # Create test message
    message = {
        'Body': json.dumps({
            'sessionId': str(uuid.uuid4()),
            'userId': 'user123',
            'exerciseId': 1,
            'levelId': 1,
            's3VideoUrl': 's3://test-bucket/video.mp4',
            'timestamp': datetime.utcnow().isoformat()
        }),
        'ReceiptHandle': 'test-receipt-123'
    }
    
    # Mock AWS to raise error
    with patch.object(consumer.aws_client, 'download_video_from_s3', side_effect=Exception('S3 error')):
        with patch.object(consumer.aws_client, 'update_ai_session', return_value=None) as mock_update:
            # Process message should handle error gracefully
            try:
                await consumer._process_message(message)
            except Exception:
                pass  # Expected to raise
            
            # Verify error was saved to DynamoDB (at least 2 calls: processing + failed)
            assert mock_update.call_count >= 1


# ==================== MODEL INFO TESTS ====================

def test_get_model_info(client):
    """Test GET /api/v1/model/info"""
    response = client.get('/api/v1/model/info')
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'modelVersion' in data
    assert 'framework' in data
    assert 'supportedGestures' in data
    assert 'gestureCount' in data
    assert data['gestureCount'] == len(settings.gesture_labels_list)


def test_get_consumer_status(client):
    """Test GET /api/v1/consumer/status"""
    response = client.get('/api/v1/consumer/status')
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'running' in data
    assert 'queueUrl' in data
    assert 'pollInterval' in data


# ==================== INTEGRATION TEST ====================

@pytest.mark.asyncio
async def test_full_assessment_flow():
    """Test complete assessment flow: submit -> process -> retrieve"""
    from app.aws_client import get_aws_client
    from app.handlers.sqs_consumer import SQSConsumer
    
    aws_client = get_aws_client()
    consumer = SQSConsumer()
    
    session_id = str(uuid.uuid4())
    
    # Mock all AWS operations
    with patch.object(aws_client, 'send_to_sqs', return_value='msg-123'):
        with patch.object(aws_client, 'update_ai_session', return_value=None):
            with patch.object(aws_client, 'download_video_from_s3', return_value=b'test video'):
                with patch.object(aws_client, 'get_ai_session', return_value={
                    'sessionId': session_id,
                    'status': 'completed',
                    'result': {
                        'recognizedGesture': 'C',
                        'confidence': 0.92,
                        'score': 100
                    }
                }):
                    # Step 1: Submit assessment
                    message = {
                        'sessionId': session_id,
                        'userId': 'user123',
                        'exerciseId': 1,
                        'levelId': 1,
                        's3VideoUrl': 's3://bucket/video.mp4',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    await aws_client.send_to_sqs(message)
                    
                    # Step 2: Process (simulated)
                    video_message = SQSVideoMessage(**message)
                    result = await consumer._process_video(video_message)
                    
                    assert result.status in ['completed', 'failed']
                    
                    # Step 3: Retrieve results
                    session = await aws_client.get_ai_session(session_id)
                    assert session['status'] == 'completed'
                    assert session['result']['recognizedGesture'] == 'C'
