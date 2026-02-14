"""
DynamoDB Local Benchmark Implementation

Key-Value benchmark implementation for AWS DynamoDB Local.
Uses boto3 client to interact with the local DynamoDB instance.
"""

import os
from typing import Dict, List, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from ..base.kv_benchmark_base import KeyValueBenchmark


class DynamoDBBenchmark(KeyValueBenchmark):
    """DynamoDB Local Key-Value benchmark implementation."""
    
    def __init__(
        self,
        endpoint_url: str = "http://localhost:8000",
        table_name: str = "benchmark_kv",
        region: str = "us-east-1"
    ):
        super().__init__(container_name="dynamodb-local")
        self.endpoint_url = endpoint_url
        self.table_name = table_name
        self.region = region
        self.client = None
        self.resource = None
        self.table = None
    
    def connect(self) -> None:
        """Connect to DynamoDB Local and create table if needed."""
        # Configure boto3 for local DynamoDB with longer timeouts
        self.client = boto3.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy',
            config=Config(
                retries={'max_attempts': 5},
                connect_timeout=30,
                read_timeout=60
            )
        )
        
        self.resource = boto3.resource(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # Create table if it doesn't exist
        self._create_table_if_not_exists()
        
        self.table = self.resource.Table(self.table_name)
        print(f"Connected to DynamoDB Local at {self.endpoint_url}")
    
    def _create_table_if_not_exists(self) -> None:
        """Create the benchmark table if it doesn't exist."""
        try:
            self.client.describe_table(TableName=self.table_name)
            print(f"Table {self.table_name} already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Creating table {self.table_name}...")
                self.client.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'pk', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'pk', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                # Wait for table to be active
                waiter = self.client.get_waiter('table_exists')
                waiter.wait(TableName=self.table_name)
                print(f"Table {self.table_name} created")
            else:
                raise
    
    def close(self) -> None:
        """Close the DynamoDB connection."""
        self.client = None
        self.resource = None
        self.table = None
        print("DynamoDB connection closed")
    
    def put(self, key: str, value: bytes) -> None:
        """Store a single key-value pair (as String for UI readability)."""
        # Convert bytes to string for readable storage
        str_value = value.decode('utf-8') if isinstance(value, bytes) else value
        self.table.put_item(
            Item={
                'pk': key,
                'data': str_value  # Store as String, not Binary
            }
        )
    
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve a value by key."""
        response = self.table.get_item(Key={'pk': key})
        item = response.get('Item')
        if item:
            data = item.get('data')
            # Convert string back to bytes for consistency
            if isinstance(data, str):
                return data.encode('utf-8')
            elif isinstance(data, bytes):
                return data
            elif hasattr(data, 'value'):
                return data.value
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair."""
        try:
            self.table.delete_item(Key={'pk': key})
            return True
        except ClientError:
            return False
    
    def batch_put(self, items: Dict[str, bytes]) -> int:
        """Store multiple key-value pairs using batch writer."""
        count = 0
        with self.table.batch_writer() as batch:
            for key, value in items.items():
                batch.put_item(
                    Item={
                        'pk': key,
                        'data': value
                    }
                )
                count += 1
        return count
    
    def batch_get(self, keys: List[str]) -> Dict[str, bytes]:
        """Retrieve multiple values by keys."""
        results = {}
        
        # Deduplicate keys (DynamoDB rejects duplicates)
        unique_keys = list(set(keys))
        
        # DynamoDB batch_get_item has a limit of 100 keys
        for i in range(0, len(unique_keys), 100):
            batch_keys = unique_keys[i:i+100]
            
            response = self.resource.batch_get_item(
                RequestItems={
                    self.table_name: {
                        'Keys': [{'pk': k} for k in batch_keys]
                    }
                }
            )
            
            for item in response.get('Responses', {}).get(self.table_name, []):
                key = item['pk']
                data = item.get('data')
                if isinstance(data, bytes):
                    results[key] = data
                elif hasattr(data, 'value'):
                    results[key] = data.value
        
        return results
    
    def scan(self, limit: int = 1000) -> List[str]:
        """Scan/list keys (up to limit)."""
        keys = []
        scan_kwargs = {
            'ProjectionExpression': 'pk',
            'Limit': limit
        }
        
        response = self.table.scan(**scan_kwargs)
        keys.extend([item['pk'] for item in response.get('Items', [])])
        
        # Handle pagination if needed and not at limit
        while 'LastEvaluatedKey' in response and len(keys) < limit:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            scan_kwargs['Limit'] = limit - len(keys)
            response = self.table.scan(**scan_kwargs)
            keys.extend([item['pk'] for item in response.get('Items', [])])
        
        return keys[:limit]
    
    def count(self) -> int:
        """Return total number of items in the table."""
        response = self.table.scan(Select='COUNT')
        count = response.get('Count', 0)
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            count += response.get('Count', 0)
        
        return count
    
    def clear(self) -> None:
        """Clear all data by deleting and recreating the table."""
        try:
            self.client.delete_table(TableName=self.table_name)
            waiter = self.client.get_waiter('table_not_exists')
            waiter.wait(TableName=self.table_name)
            print(f"Deleted table {self.table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Recreate the table
        self._create_table_if_not_exists()
        self.table = self.resource.Table(self.table_name)
        print(f"Recreated table {self.table_name}")
