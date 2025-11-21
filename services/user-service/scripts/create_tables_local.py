#!/usr/bin/env python3
"""
Create DynamoDB tables in LocalStack for local development
"""
import boto3
from botocore.exceptions import ClientError


def create_tables():
    """Create all DynamoDB tables for user-service"""
    
    # Connect to LocalStack
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    tables = [
        # UserData table
        {
            'TableName': 'UserData',
            'KeySchema': [
                {'AttributeName': 'userId', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'userId', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        # UserProgress table with GSI
        {
            'TableName': 'UserProgress',
            'KeySchema': [
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'levelId', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'levelId', 'AttributeType': 'S'},
                {'AttributeName': 'levelIdNumber', 'AttributeType': 'N'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'levelId-index',
                    'KeySchema': [
                        {'AttributeName': 'levelIdNumber', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        # AiSessions table
        {
            'TableName': 'AiSessions',
            'KeySchema': [
                {'AttributeName': 'sessionId', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'sessionId', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    ]
    
    for table_config in tables:
        table_name = table_config['TableName']
        try:
            # Check if table exists
            dynamodb.describe_table(TableName=table_name)
            print(f"✓ Table {table_name} already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Create table
                dynamodb.create_table(**table_config)
                print(f"✓ Created table {table_name}")
            else:
                raise
    
    print("\n✅ All tables created successfully!")


if __name__ == "__main__":
    create_tables()
