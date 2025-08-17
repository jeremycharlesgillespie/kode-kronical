"""
Systems Registry Service for KodeKronical Daemon

Manages the persistent registry of systems that send data to kode-kronical.
"""

import boto3
import time
import platform
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SystemsRegistryService:
    """Service for managing the systems registry table."""
    
    def __init__(self, table_name: str = "kode-kronical-systems-registry", region: str = "us-east-1"):
        """
        Initialize the systems registry service.
        
        Args:
            table_name: Name of the DynamoDB table for systems registry
            region: AWS region for DynamoDB
        """
        self.table_name = table_name
        self.region = region
        
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.table = self.dynamodb.Table(table_name)
            # Test table access
            self.table.load()
            logger.info(f"Systems registry service initialized for table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize systems registry: {e}")
            self.table = None
    
    def register_system(self, hostname: str, platform_info: Optional[str] = None) -> bool:
        """
        Register a new system or update existing system registration.
        
        Args:
            hostname: Hostname of the system
            platform_info: Platform information (e.g., 'Darwin', 'Linux')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.table:
            return False
            
        try:
            current_time = time.time()
            
            # Get current platform if not provided
            if platform_info is None:
                platform_info = platform.system()
            
            # Check if system already exists
            response = self.table.get_item(Key={'hostname': hostname})
            
            if 'Item' in response:
                # Update existing system
                self.table.update_item(
                    Key={'hostname': hostname},
                    UpdateExpression="SET last_seen = :last_seen, last_update = :last_update, active = :active",
                    ExpressionAttributeValues={
                        ':last_seen': Decimal(str(current_time)),
                        ':last_update': datetime.utcnow().isoformat(),
                        ':active': True
                    }
                )
                logger.debug(f"Updated existing system registration for {hostname}")
            else:
                # Register new system
                self.table.put_item(
                    Item={
                        'hostname': hostname,
                        'platform': platform_info,
                        'first_seen': Decimal(str(current_time)),
                        'last_seen': Decimal(str(current_time)),
                        'last_update': datetime.utcnow().isoformat(),
                        'active': True,
                        'status': 'online',
                        'cpu_percent': Decimal('0'),
                        'memory_percent': Decimal('0')
                    }
                )
                logger.info(f"Registered new system: {hostname} (platform: {platform_info})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register system {hostname}: {e}")
            return False
    
    def update_system_metrics(self, hostname: str, cpu_percent: float, memory_percent: float) -> bool:
        """
        Update system metrics in the registry.
        
        Args:
            hostname: Hostname of the system
            cpu_percent: Current CPU usage percentage
            memory_percent: Current memory usage percentage
            
        Returns:
            True if successful, False otherwise
        """
        if not self.table:
            return False
            
        try:
            current_time = time.time()
            
            self.table.update_item(
                Key={'hostname': hostname},
                UpdateExpression="SET cpu_percent = :cpu, memory_percent = :memory, last_seen = :last_seen, last_update = :last_update, #status = :status",
                ExpressionAttributeNames={
                    '#status': 'status'  # 'status' is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ':cpu': Decimal(str(cpu_percent)),
                    ':memory': Decimal(str(memory_percent)),
                    ':last_seen': Decimal(str(current_time)),
                    ':last_update': datetime.utcnow().isoformat(),
                    ':status': 'online'
                }
            )
            
            logger.debug(f"Updated metrics for {hostname}: CPU={cpu_percent}%, Memory={memory_percent}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metrics for {hostname}: {e}")
            return False
    
    def mark_system_offline(self, hostname: str) -> bool:
        """
        Mark a system as offline in the registry.
        
        Args:
            hostname: Hostname of the system
            
        Returns:
            True if successful, False otherwise
        """
        if not self.table:
            return False
            
        try:
            self.table.update_item(
                Key={'hostname': hostname},
                UpdateExpression="SET #status = :status, last_update = :last_update",
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'offline',
                    ':last_update': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Marked system {hostname} as offline")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark system {hostname} as offline: {e}")
            return False
    
    def get_system_info(self, hostname: str) -> Optional[Dict[str, Any]]:
        """
        Get information for a specific system.
        
        Args:
            hostname: Hostname of the system
            
        Returns:
            System information dict if found, None otherwise
        """
        if not self.table:
            return None
            
        try:
            response = self.table.get_item(Key={'hostname': hostname})
            
            if 'Item' in response:
                item = response['Item']
                # Convert Decimal to float for easier use
                return {
                    'hostname': item.get('hostname'),
                    'platform': item.get('platform', 'Unknown'),
                    'first_seen': float(item.get('first_seen', 0)),
                    'last_seen': float(item.get('last_seen', 0)),
                    'last_update': item.get('last_update'),
                    'active': item.get('active', True),
                    'status': item.get('status', 'unknown'),
                    'cpu_percent': float(item.get('cpu_percent', 0)),
                    'memory_percent': float(item.get('memory_percent', 0))
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get system info for {hostname}: {e}")
            return None