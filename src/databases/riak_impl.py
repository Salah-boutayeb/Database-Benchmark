"""
Riak KV Benchmark Implementation

Key-Value benchmark implementation for Riak KV.
Uses HTTP API via requests library (Python client is incompatible with Python 3.13).

Optimized for large datasets with:
- Concurrent HTTP requests via ThreadPoolExecutor
- Connection pooling with retry strategy
- Graceful error handling and exponential backoff
"""

import os
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..base.kv_benchmark_base import KeyValueBenchmark


# Tuning constants
MAX_WORKERS = 12          # Concurrent HTTP workers
POOL_CONNECTIONS = 20     # urllib3 connection pool size
POOL_MAXSIZE = 20         # Max connections per pool
RETRY_TOTAL = 3           # Number of retries per request
RETRY_BACKOFF = 0.5       # Exponential backoff factor (0.5s, 1s, 2s)
PUT_TIMEOUT = 60          # Seconds per PUT request
GET_TIMEOUT = 30          # Seconds per GET request
DELETE_TIMEOUT = 30       # Seconds per DELETE request
SCAN_TIMEOUT = 300        # Seconds for key listing (expensive)
CLEAR_BATCH_SIZE = 500    # Keys to delete in parallel per batch


class RiakBenchmark(KeyValueBenchmark):
    """Riak KV Key-Value benchmark implementation using HTTP API."""
    
    def __init__(
        self,
        host: str = "localhost",
        http_port: int = 8098,
        bucket_name: str = "benchmark_kv"
    ):
        super().__init__(container_name="benchmark_riak")
        self.host = host
        self.http_port = http_port
        self.bucket_name = bucket_name
        self.base_url = f"http://{host}:{http_port}"
        self.session = None
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with connection pooling and retry strategy."""
        session = requests.Session()
        
        # Retry strategy with exponential backoff
        retry_strategy = Retry(
            total=RETRY_TOTAL,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "PUT", "DELETE", "HEAD"],
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=POOL_CONNECTIONS,
            pool_maxsize=POOL_MAXSIZE,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def connect(self) -> None:
        """Connect to Riak KV via HTTP with connection pooling."""
        self.session = self._create_session()
        
        # Test connection with retries
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(f"{self.base_url}/ping", timeout=10)
                if response.status_code == 200:
                    print(f"Connected to Riak KV at {self.base_url}")
                    print(f"  Connection pool: {POOL_CONNECTIONS} connections, {MAX_WORKERS} workers")
                    return
                else:
                    raise ConnectionError(f"Riak ping failed: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                if attempt < max_attempts:
                    wait = attempt * 2
                    print(f"  Connection attempt {attempt}/{max_attempts} failed, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise ConnectionError(f"Cannot connect to Riak at {self.base_url} after {max_attempts} attempts: {e}")
    
    def close(self) -> None:
        """Close the Riak connection."""
        if self.session:
            self.session.close()
        self.session = None
        print("Riak connection closed")
    
    def _key_url(self, key: str) -> str:
        """Get the URL for a specific key."""
        return f"{self.base_url}/buckets/{self.bucket_name}/keys/{key}"
    
    def put(self, key: str, value: bytes) -> None:
        """Store a single key-value pair with retry."""
        response = self.session.put(
            self._key_url(key),
            data=value,
            headers={"Content-Type": "application/octet-stream"},
            timeout=PUT_TIMEOUT
        )
        response.raise_for_status()
    
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve a value by key."""
        response = self.session.get(self._key_url(key), timeout=GET_TIMEOUT)
        if response.status_code == 200:
            return response.content
        elif response.status_code == 404:
            return None
        response.raise_for_status()
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair."""
        response = self.session.delete(self._key_url(key), timeout=DELETE_TIMEOUT)
        return response.status_code in (200, 204, 404)
    
    def _put_single(self, key: str, value: bytes) -> bool:
        """Put a single key-value pair, returning success status (for concurrency)."""
        try:
            self.put(key, value)
            return True
        except Exception:
            return False
    
    def _get_single(self, key: str) -> tuple:
        """Get a single key, returning (key, value) or (key, None) (for concurrency)."""
        try:
            value = self.get(key)
            return (key, value)
        except Exception:
            return (key, None)
    
    def _delete_single(self, key: str) -> bool:
        """Delete a single key, returning success (for concurrency)."""
        try:
            return self.delete(key)
        except Exception:
            return False
    
    def batch_put(self, items: Dict[str, bytes]) -> int:
        """Store multiple key-value pairs using concurrent HTTP requests."""
        if len(items) <= 1:
            # Single item — no need for thread pool overhead
            for key, value in items.items():
                try:
                    self.put(key, value)
                    return 1
                except Exception:
                    return 0
        
        count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._put_single, key, value): key
                for key, value in items.items()
            }
            for future in as_completed(futures):
                if future.result():
                    count += 1
        return count
    
    def batch_get(self, keys: List[str]) -> Dict[str, bytes]:
        """Retrieve multiple values by keys using concurrent HTTP requests."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self._get_single, key): key for key in keys}
            for future in as_completed(futures):
                key, value = future.result()
                if value is not None:
                    results[key] = value
        
        return results
    
    def scan(self, limit: int = 1000) -> List[str]:
        """List keys in the bucket."""
        # Riak recommends against listing keys in production (expensive)
        # But for benchmarking purposes, we use the keys endpoint
        try:
            response = self.session.get(
                f"{self.base_url}/buckets/{self.bucket_name}/keys?keys=true",
                timeout=SCAN_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                keys = data.get("keys", [])
                return keys[:limit]
        except requests.exceptions.Timeout:
            print(f"  Warning: Scan timed out after {SCAN_TIMEOUT}s")
        except Exception as e:
            print(f"  Warning: Scan failed: {e}")
        return []
    
    def count(self) -> int:
        """Return total number of keys in the bucket."""
        keys = self.scan(limit=1000000)
        return len(keys)
    
    def clear(self) -> None:
        """Clear all data from the bucket using concurrent deletes."""
        print("Clearing Riak bucket...")
        keys = self.scan(limit=1000000)
        
        if not keys:
            print("  Bucket is empty")
            return
        
        deleted = 0
        total = len(keys)
        
        # Delete in concurrent batches
        for i in range(0, total, CLEAR_BATCH_SIZE):
            batch = keys[i:i + CLEAR_BATCH_SIZE]
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(self._delete_single, key) for key in batch]
                for future in as_completed(futures):
                    if future.result():
                        deleted += 1
            
            if deleted % 10000 < CLEAR_BATCH_SIZE:
                print(f"  Deleted {deleted:,}/{total:,} keys...")
        
        print(f"Cleared {deleted:,} keys from bucket {self.bucket_name}")
