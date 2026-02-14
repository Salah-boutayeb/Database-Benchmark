"""
Key-Value Database Benchmark Base Class

Abstract base class for Key-Value store benchmarks (Study n°2).
Provides a common interface for PUT, GET, DELETE, and batch operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import time
import json
import os
from datetime import datetime
from .benchmark_base import DockerResourceMonitor


class KeyValueBenchmark(ABC):
    """Abstract base class for Key-Value database benchmarks."""
    
    def __init__(self, container_name: str):
        """Initialize the KV benchmark with container name for monitoring."""
        self.container_name = container_name
        self.metrics: Dict[str, Any] = {}
        self.resource_monitor = DockerResourceMonitor(container_name)
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    def put(self, key: str, value: bytes) -> None:
        """Store a single key-value pair."""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve a value by key."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key-value pair. Returns True if deleted."""
        pass
    
    @abstractmethod
    def batch_put(self, items: Dict[str, bytes]) -> int:
        """Store multiple key-value pairs. Returns number of items stored."""
        pass
    
    @abstractmethod
    def batch_get(self, keys: List[str]) -> Dict[str, bytes]:
        """Retrieve multiple values by keys."""
        pass
    
    @abstractmethod
    def scan(self, limit: int = 1000) -> List[str]:
        """Scan/list keys (up to limit). Returns list of keys."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Return total number of keys in the store."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all data from the store."""
        pass
    
    def measure_execution_time(self, operation_name: str, func, *args, **kwargs) -> Any:
        """Measure execution time and resource usage for an operation."""
        from .resource_monitor import DockerResourceMonitor
        
        print(f"--- Starting {operation_name} ---")
        
        # Create a new monitor for this operation
        monitor = DockerResourceMonitor(self.container_name)
        monitor.start()
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        finally:
            duration = time.time() - start_time
            resources = monitor.stop()
        
        # Store metrics with full resource data (matches Study n°1 format)
        self.metrics[operation_name] = {
            "duration_seconds": round(duration, 4),
            "resources": resources
        }
        
        print(f"Finished {operation_name} in {duration:.4f} seconds")
        print(f"Container Resources: CPU avg={resources.get('container_cpu_avg', 'N/A')}%, "
               f"CPU max={resources.get('container_cpu_max', 'N/A')}%, "
               f"RAM avg={resources.get('container_mem_avg_mb', 'N/A')}MB, "
               f"RAM max={resources.get('container_mem_max_mb', 'N/A')}MB")
        
        return result
    
    def run_full_benchmark(self, num_keys: int = 1_000_000, value_size: int = 1024) -> Dict:
        """
        Run the complete Key-Value benchmark suite.
        
        Args:
            num_keys: Number of keys to insert
            value_size: Size of each value in bytes
        """
        import random
        
        print(f"\n{'='*60}")
        print(f"{self.container_name.upper()} KEY-VALUE BENCHMARK")
        print(f"{'='*60}")
        print(f"Keys: {num_keys:,} | Value size: {value_size} bytes")
        print(f"Total data: ~{(num_keys * value_size) / (1024*1024):.1f} MB")
        print(f"{'='*60}\n")
        
        # Connect
        print("--- Connecting ---")
        self.connect()
        
        # Clear existing data
        print("--- Clearing existing data ---")
        self.clear()
        
        # Generate test data
        print("--- Generating test data ---")
        def generate_value(size: int) -> bytes:
            return bytes(random.getrandbits(8) for _ in range(size))
        
        # 1. BATCH PUT - Insert all keys
        print(f"\n--- Batch PUT ({num_keys:,} keys) ---")
        batch_size = 500
        
        def do_batch_insert():
            total_inserted = 0
            for i in range(0, num_keys, batch_size):
                batch = {f"key_{j:08d}": generate_value(value_size) 
                        for j in range(i, min(i + batch_size, num_keys))}
                inserted = self.batch_put(batch)
                total_inserted += inserted
                
                if total_inserted % 100000 == 0 and total_inserted > 0:
                    print(f"  Progress: {total_inserted:,} keys inserted...")
            
            return total_inserted
        
        inserted = self.measure_execution_time("Batch PUT", do_batch_insert)
        print(f"  Inserted {inserted:,} keys")
        
        # 2. Random GET - Sample random keys
        print("\n--- Random GET (1000 keys) ---")
        sample_keys = [f"key_{random.randint(0, num_keys-1):08d}" for _ in range(1000)]
        
        def do_random_gets():
            found = 0
            for key in sample_keys:
                if self.get(key):
                    found += 1
            return found
        
        found = self.measure_execution_time("Random GET (1000)", do_random_gets)
        print(f"  Found {found}/1000 keys")
        
        # 3. BATCH GET - Get 1000 keys in batches
        print("\n--- Batch GET (1000 keys) ---")
        batch_keys = list(set([f"key_{random.randint(0, num_keys-1):08d}" for _ in range(1000)]))
        
        def do_batch_get():
            return len(self.batch_get(batch_keys))
        
        batch_found = self.measure_execution_time("Batch GET (1000)", do_batch_get)
        print(f"  Found {batch_found}/{len(batch_keys)} keys")
        
        # 4. SCAN - List keys
        print("\n--- Scan (10000 keys) ---")
        
        def do_scan():
            return len(self.scan(limit=10000))
        
        scanned = self.measure_execution_time("Scan (10000)", do_scan)
        print(f"  Scanned {scanned:,} keys")
        
        # 5. DELETE - Delete sample keys
        print("\n--- Delete (100 keys) ---")
        delete_keys = [f"key_{i:08d}" for i in range(100)]
        
        def do_deletes():
            deleted = 0
            for key in delete_keys:
                if self.delete(key):
                    deleted += 1
            return deleted
        
        deleted = self.measure_execution_time("Delete (100)", do_deletes)
        print(f"  Deleted {deleted}/100 keys")
        
        # Close connection
        self.close()
        
        # Calculate throughput
        put_duration = self.metrics.get("Batch PUT", {}).get("duration_seconds", 1)
        self.metrics["throughput"] = {
            "put_ops_per_second": round(num_keys / put_duration, 2),
            "put_mb_per_second": round((num_keys * value_size) / (1024*1024) / put_duration, 2)
        }
        
        return self.metrics
    
    def save_metrics(self, output_dir: str = "results") -> str:
        """Save metrics to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/metrics_kv_{self.container_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"\nMetrics saved to {filename}")
        return filename
    
    def _load_documents_from_file(self, file_path: str, dataset_name: str):
        """
        Load documents from file as a list of (key, bytes) tuples.
        Uses chunked reading for CSV to reduce peak memory usage.
        
        Returns:
            Tuple of (documents_list, num_docs, total_bytes)
        """
        import pandas as pd
        
        documents = []
        total_bytes = 0
        
        if file_path.endswith('.csv'):
            # Amazon CSV - read in chunks to reduce memory
            for chunk in pd.read_csv(file_path, chunksize=50000):
                for idx_in_chunk, (idx, row) in enumerate(chunk.iterrows()):
                    doc = row.to_dict()
                    doc_bytes = json.dumps(doc).encode('utf-8')
                    documents.append((f"{dataset_name}_{idx}", doc_bytes))
                    total_bytes += len(doc_bytes)
                print(f"  Loaded {len(documents):,} documents so far...")
        else:
            # Goodreads JSON lines - stream line by line
            with open(file_path, 'r', encoding='utf-8') as f:
                for idx, line in enumerate(f):
                    if line.strip():
                        doc_bytes = line.strip().encode('utf-8')
                        documents.append((f"{dataset_name}_{idx}", doc_bytes))
                        total_bytes += len(doc_bytes)
                    
                    if (idx + 1) % 500000 == 0:
                        print(f"  Loaded {len(documents):,} documents so far...")
        
        return documents, len(documents), total_bytes
    
    def run_dataset_benchmark(self, file_path: str, dataset_name: str) -> Dict:
        """
        Run benchmark using real dataset (Goodreads or Amazon).
        
        Args:
            file_path: Path to the data file (.json lines or .csv)
            dataset_name: Name of the dataset (e.g., 'goodreads', 'amazon')
        """
        import random
        
        print(f"\n{'='*60}")
        print(f"{self.container_name.upper()} KEY-VALUE BENCHMARK")
        print(f"Dataset: {dataset_name}")
        print(f"{'='*60}\n")
        
        # Connect
        print("--- Connecting ---")
        self.connect()
        
        # Clear existing data
        print("--- Clearing existing data ---")
        self.clear()
        
        # Load data from file
        print(f"--- Loading {dataset_name} data from {file_path} ---")
        documents, num_docs, total_bytes = self._load_documents_from_file(file_path, dataset_name)
        
        avg_size = total_bytes / num_docs if num_docs > 0 else 0
        
        print(f"  Loaded {num_docs:,} documents")
        print(f"  Total size: {total_bytes / (1024*1024):.1f} MB")
        print(f"  Average doc size: {avg_size:.0f} bytes")
        
        self.metrics["dataset"] = {
            "name": dataset_name,
            "documents": num_docs,
            "total_bytes": total_bytes,
            "avg_doc_size_bytes": round(avg_size, 2)
        }
        
        # 1. INSERT - Batch insert all documents
        # Use larger batches (500) — the old limit of 25 was DynamoDB-specific
        batch_size = 500
        print(f"\n--- Insert ({num_docs:,} documents, batch_size={batch_size}) ---")
        
        def do_insert():
            total_inserted = 0
            start = time.time()
            
            for i in range(0, len(documents), batch_size):
                batch = dict(documents[i:i+batch_size])
                inserted = self.batch_put(batch)
                total_inserted += inserted
                
                if total_inserted % 50000 == 0 and total_inserted > 0:
                    elapsed = time.time() - start
                    rate = total_inserted / elapsed
                    remaining = (num_docs - total_inserted) / rate if rate > 0 else 0
                    print(f"  Progress: {total_inserted:,}/{num_docs:,} "
                          f"({100*total_inserted/num_docs:.1f}%) | "
                          f"{rate:,.0f} ops/s | ETA: {remaining/60:.1f} min")
            
            return total_inserted
        
        inserted = self.measure_execution_time(f"Insert {dataset_name}", do_insert)
        print(f"  Inserted {inserted:,} documents")
        
        # 2. Skip expensive COUNT operation - use inserted count instead
        # Full table scan is too memory-intensive for large datasets
        print(f"\n--- Count (using insert count) ---")
        print(f"  Total documents: {inserted:,} (skipped expensive full scan)")
        self.metrics["Count"] = {"documents": inserted, "note": "Used insert count to avoid OOM"}
        
        # 3. READ - Random document lookups
        print("\n--- Random READ (1000 documents) ---")
        sample_keys = [doc[0] for doc in random.sample(documents, min(1000, len(documents)))]
        
        def do_random_reads():
            found = 0
            for key in sample_keys:
                value = self.get(key)
                if value:
                    found += 1
            return found
        
        found = self.measure_execution_time(f"Read {dataset_name}", do_random_reads)
        print(f"  Found {found}/{len(sample_keys)} documents")
        
        # 4. EXPORT - Full export of all documents (like MongoDB/RavenDB/ArangoDB)
        print(f"\n--- Export ALL ({num_docs:,} documents) ---")
        export_file = f"results/export_kv_{self.container_name}_{dataset_name}.json"
        
        def do_full_export():
            os.makedirs("results", exist_ok=True)
            
            exported_count = 0
            start = time.time()
            
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write('[')  # Start JSON array
                first = True
                
                # Export using the keys we already know
                for key, value in documents:
                    # Fetch from DB to simulate real export
                    data = self.get(key)
                    if data:
                        if not first:
                            f.write(',\n')
                        # Write the document
                        f.write(data.decode('utf-8') if isinstance(data, bytes) else data)
                        first = False
                        exported_count += 1
                        
                        if exported_count % 50000 == 0:
                            elapsed = time.time() - start
                            rate = exported_count / elapsed
                            remaining = (num_docs - exported_count) / rate if rate > 0 else 0
                            print(f"  Progress: {exported_count:,}/{num_docs:,} "
                                  f"({100*exported_count/num_docs:.1f}%) | "
                                  f"{rate:,.0f} docs/s | ETA: {remaining/60:.1f} min")
                
                f.write(']')  # End JSON array
            
            return exported_count
        
        exported = self.measure_execution_time(f"Export {dataset_name}", do_full_export)
        print(f"  Exported {exported:,} documents to {export_file}")
        
        # Close connection
        self.close()
        
        # Calculate throughput
        insert_metrics = self.metrics.get(f"Insert {dataset_name}", {})
        insert_duration = insert_metrics.get("duration_seconds", 1)
        self.metrics["throughput"] = {
            "insert_docs_per_second": round(num_docs / insert_duration, 2),
            "insert_mb_per_second": round(total_bytes / (1024*1024) / insert_duration, 2)
        }
        
        return self.metrics
