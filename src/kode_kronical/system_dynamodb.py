"""
DynamoDB service for uploading system performance data.
"""

import json
import time
import logging
import boto3
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime
from botocore.exceptions import ClientError

try:
    from .metrics_compression import compress_metrics_data, decompress_metrics_data, estimate_compression_ratio
except ImportError:
    # Fallback for when compression module is not available
    def compress_metrics_data(data):
        return json.dumps(data)
    
    def decompress_metrics_data(data):
        return json.loads(data) if isinstance(data, str) else data
    
    def estimate_compression_ratio(data):
        return {"error": "Compression module not available"}


logger = logging.getLogger(__name__)


class SystemDynamoDBService:
    """Service for uploading system metrics to DynamoDB."""
    
    def __init__(self, table_name: str = "kode-kronical-system", region: str = "us-east-1"):
        """Initialize DynamoDB service for system data."""
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.table_resource = boto3.resource('dynamodb', region_name=region).Table(table_name)
        
        # Ensure table exists
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the DynamoDB table exists, create if it doesn't."""
        try:
            # Check if table exists
            self.dynamodb.describe_table(TableName=self.table_name)
            logger.info(f"DynamoDB table {self.table_name} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Creating DynamoDB table {self.table_name}")
                
                # Use optimized table creation for v2 tables
                if self.table_name == "kode-kronical-system":
                    from .optimized_system_storage import OptimizedSystemStorage
                    storage = OptimizedSystemStorage(self.table_name, self.region)
                else:
                    self._create_table()
            else:
                logger.error(f"Error checking table existence: {e}")
                raise
    
    def _create_table(self):
        """Create the DynamoDB table for system data."""
        try:
            self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'N'  # Number
                    }
                ],
                BillingMode='PAY_PER_REQUEST'  # On-demand billing
            )
            
            # Wait for table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            logger.info(f"Successfully created table {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def upload_system_metrics(self, metrics_batch: List[Dict[str, Any]], hostname: str) -> bool:
        """
        Upload a batch of system metrics to DynamoDB with compression.
        
        Args:
            metrics_batch: List of system metrics dictionaries
            hostname: Hostname/machine identifier
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            if not metrics_batch:
                logger.warning("Empty metrics batch - skipping upload")
                return True
            
            # Check if we're using the optimized table structure
            if self.table_name == "kode-kronical-system":
                return self._upload_optimized_format(metrics_batch, hostname)
            else:
                return self._upload_legacy_format(metrics_batch, hostname)
                
        except Exception as e:
            logger.error(f"Failed to upload system metrics: {e}")
            return False
    
    def _upload_optimized_format(self, metrics_batch: List[Dict[str, Any]], hostname: str) -> bool:
        """Upload using optimized format (one record per minute)."""
        try:
            from .optimized_system_storage import OptimizedSystemStorage
            
            # Initialize optimized storage
            storage = OptimizedSystemStorage(self.table_name, self.region)
            
            # For optimized format, we expect only one sample (collected once per minute)
            if len(metrics_batch) == 1:
                sample = metrics_batch[0]
                system_data = sample.get('system', {})
                
                # Store the minute sample
                success = storage.store_minute_sample(hostname, system_data)
                
                if success:
                    logger.info(f"Successfully uploaded optimized minute sample for {hostname}")
                    return True
                else:
                    logger.error(f"Failed to upload optimized sample for {hostname}")
                    return False
            else:
                logger.warning(f"Expected 1 sample for optimized format, got {len(metrics_batch)}")
                # Handle multiple samples by taking the latest
                if metrics_batch:
                    latest_sample = metrics_batch[-1]  # Take the most recent
                    system_data = latest_sample.get('system', {})
                    
                    storage = OptimizedSystemStorage(self.table_name, self.region)
                    success = storage.store_minute_sample(hostname, system_data)
                    
                    if success:
                        logger.info(f"Successfully uploaded optimized sample (from {len(metrics_batch)} samples) for {hostname}")
                        return True
                    
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload optimized format: {e}")
            return False
    
    def _upload_legacy_format(self, metrics_batch: List[Dict[str, Any]], hostname: str) -> bool:
        """Upload using legacy compressed format."""
        try:
            # Create a single record for this batch
            record_id = int(time.time() * 1000)  # Use timestamp in milliseconds as ID
            
            # Compress metrics data before storing
            compressed_metrics = compress_metrics_data(metrics_batch)
            
            # Log compression statistics
            try:
                stats = estimate_compression_ratio(metrics_batch)
                if "error" not in stats:
                    logger.info(f"Compression: {stats['original_size_bytes']} -> {stats['compressed_size_bytes']} bytes "
                              f"({stats['compression_ratio_percent']}% reduction)")
            except Exception:
                pass  # Don't fail upload if compression stats fail
            
            # Prepare the record with Decimal conversion for DynamoDB
            record = {
                'id': str(record_id),
                'hostname': hostname,
                'timestamp': Decimal(str(time.time())),
                'batch_size': len(metrics_batch),
                'start_time': Decimal(str(metrics_batch[0]['timestamp'])) if metrics_batch else Decimal(str(time.time())),
                'end_time': Decimal(str(metrics_batch[-1]['timestamp'])) if metrics_batch else Decimal(str(time.time())),
                'metrics_data': compressed_metrics,  # Now compressed
                'created_at': datetime.utcnow().isoformat(),
                'data_type': 'system_metrics',
                'compressed': True  # Flag to indicate this uses new compression format
            }
            
            # Upload to DynamoDB
            self.table_resource.put_item(Item=record)
            
            # ALSO write a "latest" record for this hostname for fast lookups
            # This solves the eventual consistency problem
            # Use a hash of hostname to create a predictable numeric ID
            import hashlib
            hostname_hash = int(hashlib.md5(f'latest_{hostname}'.encode()).hexdigest()[:8], 16)
            
            latest_record = {
                'id': str(hostname_hash),  # String ID based on hostname hash
                'hostname': hostname,
                'timestamp': record['timestamp'],
                'latest_record_id': str(record_id),  # Reference to the full record
                'compressed': True,
                'record_type': 'latest_marker',  # Identify this as a marker record
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.table_resource.put_item(Item=latest_record)
            
            logger.info(f"Successfully uploaded {len(metrics_batch)} compressed system metrics to DynamoDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload system metrics to DynamoDB: {e}")
            return False
    
    def upload_single_metric(self, metric: Dict[str, Any], hostname: str) -> bool:
        """
        Upload a single system metric to DynamoDB.
        
        Args:
            metric: Single system metric dictionary
            hostname: Hostname/machine identifier
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        return self.upload_system_metrics([metric], hostname)
    
    def get_recent_metrics(self, hostname: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent system metrics from DynamoDB.
        
        Args:
            hostname: Optional hostname filter
            hours: Number of hours to look back
            
        Returns:
            List of system metrics records
        """
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            # Build scan parameters
            scan_params = {
                'FilterExpression': '#ts > :cutoff_time',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {':cutoff_time': cutoff_time}
            }
            
            # Add hostname filter if provided
            if hostname:
                scan_params['FilterExpression'] += ' AND hostname = :hostname'
                scan_params['ExpressionAttributeValues'][':hostname'] = hostname
            
            response = self.table_resource.scan(**scan_params)
            
            records = response.get('Items', [])
            
            # Parse metrics_data JSON for each record (handle both compressed and uncompressed)
            for record in records:
                if 'metrics_data' in record:
                    try:
                        # Check if this record uses compression
                        if record.get('compressed', False):
                            record['parsed_metrics'] = decompress_metrics_data(record['metrics_data'])
                        else:
                            # Backward compatibility: handle old uncompressed format
                            record['parsed_metrics'] = json.loads(record['metrics_data'])
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Failed to parse metrics_data for record {record.get('id')}: {e}")
                        record['parsed_metrics'] = []
            
            logger.info(f"Retrieved {len(records)} system metrics records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to retrieve system metrics: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test DynamoDB connection and table access."""
        try:
            # Try to describe the table
            response = self.dynamodb.describe_table(TableName=self.table_name)
            table_status = response['Table']['TableStatus']
            
            if table_status == 'ACTIVE':
                logger.info(f"DynamoDB connection successful. Table {self.table_name} is active.")
                return True
            else:
                logger.warning(f"Table {self.table_name} is in status: {table_status}")
                return False
                
        except Exception as e:
            logger.error(f"DynamoDB connection test failed: {e}")
            return False