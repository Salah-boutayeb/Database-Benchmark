"""
Abstract Base Class for Database Benchmarks.

This module defines the contract that all database implementations must follow,
while providing reusable concrete methods for common operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json
import os
import time

from .resource_monitor import DockerResourceMonitor


class DatabaseBenchmark(ABC):
    """
    Abstract Base Class for database benchmarking.
    
    Concrete Methods (DRY - shared logic):
        - measure_execution_time: Times operations with resource monitoring
        - save_results: Writes benchmark results to JSON
        - run_full_benchmark: Template method orchestrating the benchmark flow
        - print_summary: Displays formatted results
    
    Abstract Methods (must be implemented by subclasses):
        - connect: Establish database connection
        - insert_data: Bulk insert documents
        - read_data: Read operations (find one, find many)
        - update_data: Update operations
        - delete_data: Delete operations
        - export_data: Export collection to file
        - close: Close database connection
    """

    def __init__(self, db_name: str, container_name: str, base_dir: str):
        """
        Initialize the benchmark.
        
        Args:
            db_name: Human-readable database name (e.g., "MongoDB")
            container_name: Docker container name for resource monitoring
            base_dir: Base directory for data and results
        """
        self.db_name = db_name
        self.container_name = container_name
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.results_dir = os.path.join(base_dir, 'results')
        self.metrics: Dict[str, Any] = {}
        self.connection: Optional[Any] = None
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)

    # ==================== CONCRETE METHODS (DRY) ====================

    def measure_execution_time(self, operation_name: str, func: callable, *args, **kwargs) -> Any:
        """
        Measure execution time and resource usage of an operation.
        
        Args:
            operation_name: Human-readable name for the operation
            func: The function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        print(f"--- Starting {operation_name} ---")
        monitor = DockerResourceMonitor(self.container_name)
        monitor.start()

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"Error during {operation_name}: {e}")
            import traceback
            traceback.print_exc()
            result = None
        end_time = time.time()

        resources = monitor.stop()
        duration = end_time - start_time

        print(f"Finished {operation_name} in {duration:.4f} seconds")
        print(f"Container Resources: CPU avg={resources['container_cpu_avg']}%, "
              f"RAM avg={resources['container_mem_avg_mb']}MB")

        self.metrics[operation_name] = {
            "duration_seconds": round(duration, 4),
            "resources": resources
        }
        
        return result

    def save_results(self, suffix: str = "") -> str:
        """
        Save benchmark results to a JSON file.
        
        Args:
            suffix: Optional suffix for the filename
            
        Returns:
            Path to the saved file
        """
        filename = f"metrics_{self.db_name.lower()}{suffix}.json"
        results_path = os.path.join(self.results_dir, filename)
        
        with open(results_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"\nMetrics saved to {results_path}")
        return results_path

    def print_summary(self) -> None:
        """Print a formatted summary of the benchmark results."""
        print("\n" + "=" * 60)
        print(f"{self.db_name.upper()} BENCHMARK SUMMARY")
        print("=" * 60)
        
        for op, data in self.metrics.items():
            res = data['resources']
            print(f"{op}: {data['duration_seconds']:.4f}s | "
                  f"CPU avg: {res['container_cpu_avg']}% | "
                  f"RAM avg: {res['container_mem_avg_mb']}MB")

    def run_full_benchmark(self, datasets: list) -> None:
        """
        Template method that orchestrates the full benchmark flow.
        
        Args:
            datasets: List of tuples (file_path, collection_name, dataset_label)
        """
        try:
            # 1. Connect
            print(f"\n{'='*60}")
            print(f"Starting {self.db_name} Benchmark")
            print(f"{'='*60}")
            self.connect()

            # 2. Run benchmarks for each dataset
            for file_path, collection_name, label in datasets:
                if not os.path.exists(file_path):
                    print(f"Dataset not found: {file_path}")
                    continue
                    
                print(f"\n=== Benchmarking {label} Dataset ===")
                
                # Insert
                self.measure_execution_time(
                    f"Import {label}",
                    self.insert_data, file_path, collection_name
                )
                
                # CRUD (Read, Update, Delete)
                self.measure_execution_time(
                    f"CRUD {label}",
                    self._run_crud, collection_name
                )
                
                # Export
                self.measure_execution_time(
                    f"Export {label}",
                    self.export_data, collection_name
                )

            # 3. Save results and print summary
            self.save_results("")
            self.print_summary()

        except Exception as e:
            print(f"Benchmark error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 4. Close connection
            self.close()

    def _run_crud(self, collection_name: str) -> None:
        """Internal method to run all CRUD operations."""
        self.read_data(collection_name)
        self.update_data(collection_name)
        self.delete_data(collection_name)

    # ==================== ABSTRACT METHODS (Interface) ====================

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def insert_data(self, file_path: str, collection_name: str) -> int:
        """
        Insert data from file into the collection.
        
        Args:
            file_path: Path to the data file (JSON lines or CSV)
            collection_name: Target collection/table name
            
        Returns:
            Number of documents inserted
        """
        pass

    @abstractmethod
    def read_data(self, collection_name: str) -> None:
        """
        Perform read operations on the collection.
        
        Args:
            collection_name: Collection to read from
        """
        pass

    @abstractmethod
    def update_data(self, collection_name: str) -> int:
        """
        Perform update operations on the collection.
        
        Args:
            collection_name: Collection to update
            
        Returns:
            Number of documents updated
        """
        pass

    @abstractmethod
    def delete_data(self, collection_name: str) -> int:
        """
        Perform delete operations on the collection.
        
        Args:
            collection_name: Collection to delete from
            
        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    def export_data(self, collection_name: str) -> str:
        """
        Export collection to a file.
        
        Args:
            collection_name: Collection to export
            
        Returns:
            Path to the exported file
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection and release resources."""
        pass
