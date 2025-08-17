"""
Metrics data compression utilities for kode-kronical DynamoDB storage.

Focuses on reducing duplication and shortening data to minimize storage costs.
"""

import json
from typing import Dict, List, Any, Tuple
from decimal import Decimal


# Field name compression mapping (most impactful)
FIELD_COMPRESS_MAP = {
    # System metrics
    'timestamp': 't',
    'cpu_percent': 'c',
    'memory_percent': 'mp',
    'memory_available_mb': 'ma',
    'memory_used_mb': 'mu',
    
    # Process metrics
    'memory_rss_mb': 'mr',
    'memory_vms_mb': 'mv',
    'num_threads': 'nt',
    'create_time': 'ct',
    'cmdline': 'cmd',
    
    # Network metrics
    'bytes_sent': 'bs',
    'bytes_recv': 'br',
    'packets_sent': 'ps',
    'packets_recv': 'pr',
    'active_connections': 'ac',
    
    # Common fields
    'processes': 'procs',
    'network': 'net',
    'system': 'sys'
}

# Reverse mapping for decompression
FIELD_DECOMPRESS_MAP = {v: k for k, v in FIELD_COMPRESS_MAP.items()}

# Status compression
STATUS_COMPRESS_MAP = {
    'running': 'r',
    'sleeping': 's',
    'zombie': 'z',
    'stopped': 't',
    'disk-sleep': 'd',
    'idle': 'i'
}

STATUS_DECOMPRESS_MAP = {v: k for k, v in STATUS_COMPRESS_MAP.items()}


def compress_field_names(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively compress field names in a dictionary.
    
    Args:
        data: Dictionary with verbose field names
        
    Returns:
        Dictionary with compressed field names
    """
    if not isinstance(data, dict):
        return data
    
    compressed = {}
    for key, value in data.items():
        # Compress the key name
        new_key = FIELD_COMPRESS_MAP.get(key, key)
        
        # Recursively compress nested structures
        if isinstance(value, dict):
            compressed[new_key] = compress_field_names(value)
        elif isinstance(value, list):
            compressed[new_key] = [compress_field_names(item) if isinstance(item, dict) else item for item in value]
        else:
            compressed[new_key] = value
    
    return compressed


def decompress_field_names(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively decompress field names in a dictionary.
    
    Args:
        data: Dictionary with compressed field names
        
    Returns:
        Dictionary with original field names
    """
    if not isinstance(data, dict):
        return data
    
    decompressed = {}
    for key, value in data.items():
        # Decompress the key name
        new_key = FIELD_DECOMPRESS_MAP.get(key, key)
        
        # Recursively decompress nested structures
        if isinstance(value, dict):
            decompressed[new_key] = decompress_field_names(value)
        elif isinstance(value, list):
            decompressed[new_key] = [decompress_field_names(item) if isinstance(item, dict) else item for item in value]
        else:
            decompressed[new_key] = value
    
    return decompressed


def reduce_precision(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reduce decimal precision in numeric values to save space.
    
    Args:
        data: Dictionary with full precision numbers
        
    Returns:
        Dictionary with reduced precision numbers
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = reduce_precision(value)
        elif isinstance(value, list):
            result[key] = [reduce_precision(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, float):
            # Reduce precision based on field type
            if key in ['c', 'cpu_percent']:  # CPU percentage
                result[key] = round(value, 1)
            elif key in ['t', 'timestamp', 'ct', 'create_time']:  # Timestamps
                result[key] = round(value, 1)  # 0.1 second precision
            elif 'mb' in key or key in ['ma', 'mu', 'mr', 'mv']:  # Memory in MB
                result[key] = int(round(value))  # Round to whole MB
            elif key in ['mp', 'memory_percent']:  # Memory percentage
                result[key] = round(value, 1)
            else:
                result[key] = round(value, 2)  # Default to 2 decimal places
        else:
            result[key] = value
    
    return result


def compress_status_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compress process status strings to single characters.
    
    Args:
        data: Dictionary potentially containing status fields
        
    Returns:
        Dictionary with compressed status values
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = compress_status_values(value)
        elif isinstance(value, list):
            result[key] = [compress_status_values(item) if isinstance(item, dict) else item for item in value]
        elif key == 'status' and isinstance(value, str):
            result[key] = STATUS_COMPRESS_MAP.get(value, value)
        else:
            result[key] = value
    
    return result


def decompress_status_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decompress process status characters back to full strings.
    
    Args:
        data: Dictionary with compressed status values
        
    Returns:
        Dictionary with full status strings
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = decompress_status_values(value)
        elif isinstance(value, list):
            result[key] = [decompress_status_values(item) if isinstance(item, dict) else item for item in value]
        elif key == 'status' and isinstance(value, str):
            result[key] = STATUS_DECOMPRESS_MAP.get(value, value)
        else:
            result[key] = value
    
    return result


def extract_static_process_metadata(metrics_data: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract static process metadata to avoid duplication across samples.
    
    Args:
        metrics_data: List of metric samples
        
    Returns:
        Tuple of (static_metadata, compressed_samples)
    """
    if not metrics_data or not isinstance(metrics_data[0], dict):
        return {}, metrics_data
    
    # Collect process metadata from first sample
    static_metadata = {'procs': {}}
    first_sample = metrics_data[0]
    
    if 'processes' in first_sample:
        for pid, proc_data in first_sample['processes'].items():
            if isinstance(proc_data, dict):
                # Extract static fields
                static_fields = {}
                for field in ['name', 'cmdline', 'create_time']:
                    if field in proc_data:
                        static_fields[field] = proc_data[field]
                
                if static_fields:
                    static_metadata['procs'][pid] = static_fields
    
    # Remove static fields from all samples
    compressed_samples = []
    for sample in metrics_data:
        if isinstance(sample, dict) and 'processes' in sample:
            compressed_sample = sample.copy()
            compressed_sample['processes'] = {}
            
            for pid, proc_data in sample['processes'].items():
                if isinstance(proc_data, dict):
                    # Keep only dynamic fields
                    dynamic_data = {}
                    for field, value in proc_data.items():
                        if field not in ['name', 'cmdline', 'create_time']:
                            dynamic_data[field] = value
                    
                    if dynamic_data:
                        compressed_sample['processes'][pid] = dynamic_data
            
            compressed_samples.append(compressed_sample)
        else:
            compressed_samples.append(sample)
    
    return static_metadata, compressed_samples


def restore_static_process_metadata(static_metadata: Dict[str, Any], compressed_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Restore static process metadata to compressed samples.
    
    Args:
        static_metadata: Static process metadata
        compressed_samples: Samples with only dynamic data
        
    Returns:
        Full samples with static metadata restored
    """
    if not static_metadata.get('procs'):
        return compressed_samples
    
    restored_samples = []
    for sample in compressed_samples:
        if isinstance(sample, dict) and 'processes' in sample:
            restored_sample = sample.copy()
            restored_sample['processes'] = {}
            
            for pid, dynamic_data in sample['processes'].items():
                if isinstance(dynamic_data, dict):
                    # Merge static and dynamic data
                    full_data = {}
                    
                    # Add static metadata if available
                    if pid in static_metadata['procs']:
                        full_data.update(static_metadata['procs'][pid])
                    
                    # Add dynamic data
                    full_data.update(dynamic_data)
                    
                    restored_sample['processes'][pid] = full_data
            
            restored_samples.append(restored_sample)
        else:
            restored_samples.append(sample)
    
    return restored_samples


def compress_metrics_data(metrics_data: List[Dict[str, Any]]) -> str:
    """
    Apply all compression techniques to metrics data.
    
    Args:
        metrics_data: Raw metrics data list
        
    Returns:
        Compressed JSON string for DynamoDB storage
    """
    if not metrics_data:
        return json.dumps([])
    
    # Step 1: Extract static process metadata (reduces duplication)
    static_metadata, compressed_samples = extract_static_process_metadata(metrics_data)
    
    # Step 2: Reduce precision (saves space)
    compressed_samples = [reduce_precision(sample) for sample in compressed_samples]
    
    # Step 3: Compress status values
    compressed_samples = [compress_status_values(sample) for sample in compressed_samples]
    
    # Step 4: Compress field names (biggest space saver)
    compressed_samples = [compress_field_names(sample) for sample in compressed_samples]
    static_metadata = compress_field_names(static_metadata)
    
    # Create final compressed structure
    compressed_data = {
        'meta': static_metadata,
        'samples': compressed_samples
    }
    
    return json.dumps(compressed_data, separators=(',', ':'))  # No spaces in JSON


def decompress_metrics_data(compressed_json: str) -> List[Dict[str, Any]]:
    """
    Decompress metrics data back to original format.
    
    Args:
        compressed_json: Compressed JSON string from DynamoDB
        
    Returns:
        Original metrics data format
    """
    try:
        compressed_data = json.loads(compressed_json)
        
        # Handle old uncompressed format (backward compatibility)
        if isinstance(compressed_data, list):
            return compressed_data
        
        # Extract components
        static_metadata = compressed_data.get('meta', {})
        compressed_samples = compressed_data.get('samples', [])
        
        # Reverse compression steps
        # Step 1: Decompress field names
        static_metadata = decompress_field_names(static_metadata)
        decompressed_samples = [decompress_field_names(sample) for sample in compressed_samples]
        
        # Step 2: Decompress status values
        decompressed_samples = [decompress_status_values(sample) for sample in decompressed_samples]
        
        # Step 3: Restore static process metadata
        full_samples = restore_static_process_metadata(static_metadata, decompressed_samples)
        
        return full_samples
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error decompressing metrics data: {e}")
        return []


def estimate_compression_ratio(original_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate compression ratio for given data.
    
    Args:
        original_data: Original metrics data
        
    Returns:
        Compression statistics
    """
    if not original_data:
        return {"error": "No data provided"}
    
    original_json = json.dumps(original_data, separators=(',', ':'))
    original_size = len(original_json.encode('utf-8'))
    
    compressed_json = compress_metrics_data(original_data)
    compressed_size = len(compressed_json.encode('utf-8'))
    
    ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    
    return {
        "original_size_bytes": original_size,
        "compressed_size_bytes": compressed_size,
        "compression_ratio_percent": round(ratio, 1),
        "size_reduction_bytes": original_size - compressed_size,
        "samples_count": len(original_data)
    }