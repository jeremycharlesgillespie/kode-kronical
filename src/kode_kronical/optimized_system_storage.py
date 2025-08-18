"""
Optimized system metrics storage service for frontend consumption.

This service stores data in a structure that's optimized for frontend queries:
- One record per minute per hostname
- Direct format that matches frontend expectations
- Minimal processing required by Django
- Efficient queries using time-based partition keys
"""

import json
import time
import logging
import boto3
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class OptimizedSystemStorage:
    """Optimized storage service for system metrics."""
    
    def __init__(self, table_name: str = "kode-kronical-system", region: str = "us-east-1"):
        """Initialize optimized DynamoDB service."""
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.table_resource = boto3.resource('dynamodb', region_name=region).Table(table_name)
        
        # Registry table for persistent system tracking
        self.registry_table_name = "kode-kronical-systems-registry"
        self.registry_table = boto3.resource('dynamodb', region_name=region).Table(self.registry_table_name)
        
        # Ensure table exists
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the optimized DynamoDB table exists, create if it doesn't."""
        try:
            # Check if table exists
            self.dynamodb.describe_table(TableName=self.table_name)
            logger.info(f"Optimized DynamoDB table {self.table_name} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Creating optimized DynamoDB table {self.table_name}")
                self._create_optimized_table()
            else:
                raise
    
    def _create_optimized_table(self):
        """Create optimized DynamoDB table structure."""
        table_config = {
            'TableName': self.table_name,
            'KeySchema': [
                {
                    'AttributeName': 'hostname_hour',  # Partition key: hostname#2025-01-06-15
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'minute_timestamp',  # Sort key: Unix timestamp rounded to minute
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'hostname_hour',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'minute_timestamp',
                    'AttributeType': 'N'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {
                    'Key': 'Application',
                    'Value': 'kode-kronical'
                },
                {
                    'Key': 'Version',
                    'Value': 'v2-optimized'
                }
            ]
        }
        
        try:
            self.dynamodb.create_table(**table_config)
            logger.info(f"Created optimized table {self.table_name}")
            
            # Wait for table to be active
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            logger.info(f"Table {self.table_name} is now active")
            
        except Exception as e:
            logger.error(f"Failed to create optimized table {self.table_name}: {e}")
            raise
    
    def store_minute_sample(self, hostname: str, system_metrics: Dict[str, Any]) -> bool:
        """
        Store a single minute sample for a hostname.
        
        Args:
            hostname: System hostname
            system_metrics: Dict containing cpu_percent, memory_percent, etc.
            
        Returns:
            bool: Success status
        """
        try:
            current_time = time.time()
            minute_timestamp = int(current_time // 60) * 60  # Round down to minute boundary
            
            # Create hour-based partition key for efficient queries
            dt = datetime.fromtimestamp(minute_timestamp, tz=timezone.utc)
            hostname_hour = f"{hostname}#{dt.strftime('%Y-%m-%d-%H')}"
            
            # Create frontend-ready record with TTL (30 days from now)
            ttl_timestamp = int(current_time + (30 * 24 * 60 * 60))  # 30 days in seconds
            
            record = {
                'hostname_hour': hostname_hour,
                'minute_timestamp': minute_timestamp,
                'hostname': hostname,
                'timestamp': minute_timestamp,  # For backward compatibility
                'cpu_percent': round(system_metrics.get('cpu_percent', 0), 1),
                'memory_percent': round(system_metrics.get('memory_percent', 0), 1),
                'memory_available_mb': int(system_metrics.get('memory_available_mb', 0)),
                'memory_used_mb': int(system_metrics.get('memory_used_mb', 0)),
                'collected_at': current_time,  # When the sample was actually taken
                'created_at': datetime.utcnow().isoformat(),
                'ttl': ttl_timestamp  # TTL for automatic deletion after 30 days
            }
            
            # Convert to DynamoDB format
            dynamodb_item = self._convert_to_dynamodb_item(record)
            
            # Store in DynamoDB
            self.table_resource.put_item(Item=dynamodb_item)
            
            # Update registry with this system
            self._update_system_registry(hostname, system_metrics)
            
            logger.debug(f"Stored minute sample for {hostname} at {minute_timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store minute sample for {hostname}: {e}")
            return False
    
    def _update_system_registry(self, hostname: str, system_metrics: Dict[str, Any]) -> None:
        """Update the system registry with latest info for this hostname."""
        try:
            current_time = time.time()
            
            # Get system info - you can expand this with more details
            import platform
            system_info = {
                'hostname': hostname,
                'last_seen': Decimal(str(current_time)),
                'last_update': datetime.utcnow().isoformat(),
                'cpu_percent': Decimal(str(round(system_metrics.get('cpu_percent', 0), 1))),
                'memory_percent': Decimal(str(round(system_metrics.get('memory_percent', 0), 1))),
                'status': 'online',
                'first_seen': Decimal(str(current_time)),  # Will be preserved on updates
                'platform': platform.system() if 'platform' in dir() else 'Unknown',
                'active': True  # Can be set to False to hide from dashboard
            }
            
            # Use UpdateItem to preserve first_seen if it exists
            self.registry_table.update_item(
                Key={'hostname': hostname},
                UpdateExpression='SET last_seen = :last_seen, last_update = :last_update, '
                                'cpu_percent = :cpu, memory_percent = :mem, #status = :status, '
                                'platform = :platform, active = :active, '
                                'first_seen = if_not_exists(first_seen, :first_seen)',
                ExpressionAttributeNames={
                    '#status': 'status'  # status is a reserved word
                },
                ExpressionAttributeValues={
                    ':last_seen': system_info['last_seen'],
                    ':last_update': system_info['last_update'],
                    ':cpu': system_info['cpu_percent'],
                    ':mem': system_info['memory_percent'],
                    ':status': system_info['status'],
                    ':platform': system_info['platform'],
                    ':active': system_info['active'],
                    ':first_seen': system_info['first_seen']
                }
            )
            logger.debug(f"Updated registry for {hostname}")
            
        except Exception as e:
            logger.warning(f"Failed to update registry for {hostname}: {e}")
            # Don't fail the main operation if registry update fails
    
    def _convert_to_dynamodb_item(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Convert record to DynamoDB item format."""
        dynamodb_item = {}
        
        for key, value in record.items():
            if isinstance(value, float):
                dynamodb_item[key] = Decimal(str(value))
            elif isinstance(value, int):
                dynamodb_item[key] = value
            elif isinstance(value, str):
                dynamodb_item[key] = value
            else:
                dynamodb_item[key] = str(value)
        
        return dynamodb_item
    
    def get_recent_data(self, hostname: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent data for a hostname - optimized for frontend consumption.
        
        Args:
            hostname: System hostname
            hours: Hours of data to retrieve
            
        Returns:
            List of minute-level data points ready for frontend
        """
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            # Generate list of hour partitions to query
            start_dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
            current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
            
            all_records = []
            
            # Query each hour partition
            hour_dt = start_dt.replace(minute=0, second=0, microsecond=0)
            while hour_dt <= current_dt:
                hostname_hour = f"{hostname}#{hour_dt.strftime('%Y-%m-%d-%H')}"
                
                # Query this hour's data
                response = self.table_resource.query(
                    KeyConditionExpression='hostname_hour = :hostname_hour AND minute_timestamp >= :start_time',
                    ExpressionAttributeValues={
                        ':hostname_hour': hostname_hour,
                        ':start_time': int(start_time)
                    }
                )
                
                hour_records = response.get('Items', [])
                all_records.extend(hour_records)
                
                # Move to next hour
                hour_dt = hour_dt.replace(hour=hour_dt.hour + 1)
                if hour_dt.hour == 0:
                    hour_dt = hour_dt.replace(day=hour_dt.day + 1)
            
            # Convert DynamoDB items back to regular dicts
            records = []
            for item in all_records:
                record = self._convert_from_dynamodb_item(item)
                records.append(record)
            
            # Sort by timestamp
            records.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Retrieved {len(records)} optimized records for {hostname}")
            return records
            
        except Exception as e:
            logger.error(f"Failed to retrieve optimized data for {hostname}: {e}")
            return []
    
    def _convert_from_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item back to regular dict."""
        record = {}
        
        for key, value in item.items():
            if isinstance(value, Decimal):
                record[key] = float(value)
            else:
                record[key] = value
        
        return record
    
    def get_latest_for_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Get the latest data point for a hostname."""
        try:
            # Get current hour partition
            current_time = time.time()
            current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
            hostname_hour = f"{hostname}#{current_dt.strftime('%Y-%m-%d-%H')}"
            
            # Query latest record from current hour
            response = self.table_resource.query(
                KeyConditionExpression='hostname_hour = :hostname_hour',
                ExpressionAttributeValues={
                    ':hostname_hour': hostname_hour
                },
                ScanIndexForward=False,  # Descending order (latest first)
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return self._convert_from_dynamodb_item(items[0])
            
            # If no data in current hour, check previous hour
            prev_hour_dt = current_dt.replace(hour=current_dt.hour - 1)
            if prev_hour_dt.hour == 23 and current_dt.hour == 0:
                prev_hour_dt = prev_hour_dt.replace(day=prev_hour_dt.day - 1)
                
            prev_hostname_hour = f"{hostname}#{prev_hour_dt.strftime('%Y-%m-%d-%H')}"
            
            response = self.table_resource.query(
                KeyConditionExpression='hostname_hour = :hostname_hour',
                ExpressionAttributeValues={
                    ':hostname_hour': prev_hostname_hour
                },
                ScanIndexForward=False,
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return self._convert_from_dynamodb_item(items[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest data for {hostname}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to optimized storage."""
        try:
            response = self.dynamodb.describe_table(TableName=self.table_name)
            return response['Table']['TableStatus'] == 'ACTIVE'
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False