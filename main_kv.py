#!/usr/bin/env python3
"""
Key-Value Database Benchmark Runner

Main entry point for Study n°2: Key-Value database benchmarks.
Compares DynamoDB Local vs Riak KV using real datasets (Goodreads/Amazon).

Usage:
    # With real datasets (like Study n°1)
    python main_kv.py --dataset goodreads amazon
    python main_kv.py --db dynamodb --dataset goodreads
    
    # With synthetic data
    python main_kv.py --db dynamodb riak --keys 100000
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dataset paths (same as Study n°1)
DATASETS = {
    "goodreads": "data/goodreads_reviews_mystery_thriller_crime.json",
    "amazon": "data/amazon_reviews.csv"
}


def get_dynamodb_benchmark():
    """Create DynamoDB benchmark instance."""
    from src.databases.dynamodb_impl import DynamoDBBenchmark
    return DynamoDBBenchmark(
        endpoint_url="http://localhost:8000",
        table_name="benchmark_kv"
    )


def get_riak_benchmark():
    """Create Riak benchmark instance."""
    from src.databases.riak_impl import RiakBenchmark
    return RiakBenchmark(
        host="localhost",
        http_port=8098,
        bucket_name="benchmark_kv"
    )


def run_dataset_benchmark(db_name: str, dataset_name: str) -> Dict[str, Any]:
    """Run benchmark for a single database using real dataset."""
    print(f"\n{'#'*70}")
    print(f"# BENCHMARKING: {db_name.upper()}")
    print(f"# Dataset: {dataset_name}")
    print(f"{'#'*70}\n")
    
    # Get the appropriate benchmark instance
    if db_name == "dynamodb":
        benchmark = get_dynamodb_benchmark()
    elif db_name == "riak":
        benchmark = get_riak_benchmark()
    else:
        raise ValueError(f"Unknown database: {db_name}")
    
    # Get dataset path
    file_path = DATASETS.get(dataset_name)
    if not file_path or not os.path.exists(file_path):
        print(f"Error: Dataset file not found: {file_path}")
        return {"error": f"Dataset not found: {file_path}"}
    
    try:
        # Run the benchmark with real data
        metrics = benchmark.run_dataset_benchmark(
            file_path=file_path,
            dataset_name=dataset_name
        )
        
        # Save metrics
        benchmark.save_metrics("results")
        
        return metrics
        
    except Exception as e:
        print(f"\nError benchmarking {db_name} with {dataset_name}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def run_synthetic_benchmark(db_name: str, num_keys: int, value_size: int) -> Dict[str, Any]:
    """Run benchmark for a single database using synthetic data."""
    print(f"\n{'#'*70}")
    print(f"# BENCHMARKING: {db_name.upper()}")
    print(f"# Keys: {num_keys:,} | Value size: {value_size} bytes")
    print(f"{'#'*70}\n")
    
    # Get the appropriate benchmark instance
    if db_name == "dynamodb":
        benchmark = get_dynamodb_benchmark()
    elif db_name == "riak":
        benchmark = get_riak_benchmark()
    else:
        raise ValueError(f"Unknown database: {db_name}")
    
    try:
        # Run the benchmark
        metrics = benchmark.run_full_benchmark(
            num_keys=num_keys,
            value_size=value_size
        )
        
        # Save metrics
        benchmark.save_metrics("results")
        
        return metrics
        
    except Exception as e:
        print(f"\nError benchmarking {db_name}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def save_all_metrics(results: Dict[str, Any], output_dir: str = "results") -> None:
    """Save combined metrics from all databases."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/all_kv_metrics_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nAll KV metrics saved to: {filename}")


def print_comparison(results: Dict[str, Any], use_datasets: bool = False) -> None:
    """Print a comparison table of results."""
    print("\n" + "="*70)
    print("KEY-VALUE BENCHMARK COMPARISON")
    print("="*70)
    
    # Get runs that completed successfully
    successful = [(key, metrics) for key, metrics in results.items() if "error" not in metrics]
    
    if not successful:
        print("No successful benchmarks to compare.")
        return
    
    if use_datasets:
        # Dataset mode: show Insert/Read times + resources
        print(f"\n{'DB + Dataset':<30} {'Insert (s)':<12} {'MB/s':<10} {'Read (s)':<12} {'CPU avg%':<10} {'RAM avg MB':<12}")
        print("-"*86)
        
        for key, metrics in successful:
            insert_key = next((k for k in metrics.keys() if k.startswith("Insert ")), None)
            read_key = next((k for k in metrics.keys() if k.startswith("Read ")), None)
            
            insert_data = metrics.get(insert_key, {}) if insert_key else {}
            read_data = metrics.get(read_key, {}) if read_key else {}
            
            insert_time = insert_data.get("duration_seconds", "N/A")
            insert_mbps = metrics.get("throughput", {}).get("insert_mb_per_second", "N/A")
            read_time = read_data.get("duration_seconds", "N/A")
            
            # Get resource metrics from the insert operation (longest running)
            resources = insert_data.get("resources", {})
            cpu_avg = resources.get("container_cpu_avg", "N/A")
            mem_avg = resources.get("container_mem_avg_mb", "N/A")
            
            insert_str = f"{insert_time:.2f}" if isinstance(insert_time, (int, float)) else str(insert_time)
            read_str = f"{read_time:.4f}" if isinstance(read_time, (int, float)) else str(read_time)
            cpu_str = f"{cpu_avg:.1f}" if isinstance(cpu_avg, (int, float)) else str(cpu_avg)
            mem_str = f"{mem_avg:.1f}" if isinstance(mem_avg, (int, float)) else str(mem_avg)
                
            print(f"{key:<30} {insert_str:<12} {insert_mbps:<10} {read_str:<12} {cpu_str:<10} {mem_str:<12}")
    else:
        # Synthetic mode: show PUT/GET times
        print(f"\n{'Operation':<25} ", end="")
        dbs = [key for key, _ in successful]
        for db in dbs:
            print(f"{db.upper():<20}", end="")
        print("\n" + "-"*70)
        
        operations = ["Batch PUT", "Random GET (1000)", "Batch GET (1000)", "Scan (10000)", "Delete (100)"]
        
        for op in operations:
            print(f"{op:<25} ", end="")
            for key, metrics in successful:
                if op in metrics:
                    duration = metrics[op].get("duration_seconds", "N/A")
                    if isinstance(duration, (int, float)):
                        print(f"{duration:>8.4f}s          ", end="")
                    else:
                        print(f"{'N/A':>20}", end="")
                else:
                    print(f"{'N/A':>20}", end="")
            print()
        
        # Throughput comparison
        print("\n" + "-"*70)
        print("THROUGHPUT:")
        for key, metrics in successful:
            throughput = metrics.get("throughput", {})
            ops_per_sec = throughput.get("put_ops_per_second", 0)
            mb_per_sec = throughput.get("put_mb_per_second", 0)
            print(f"  {key.upper()}: {ops_per_sec:,.0f} ops/s | {mb_per_sec:.2f} MB/s")


def main():
    parser = argparse.ArgumentParser(
        description="Key-Value Database Benchmark (Study n°2)"
    )
    parser.add_argument(
        "--db",
        nargs="+",
        choices=["dynamodb", "riak"],
        default=["dynamodb", "riak"],
        help="Databases to benchmark (default: all)"
    )
    parser.add_argument(
        "--dataset",
        nargs="+",
        choices=["goodreads", "amazon"],
        help="Use real datasets: goodreads and/or amazon"
    )
    parser.add_argument(
        "--keys",
        type=int,
        default=100000,
        help="Number of keys for synthetic benchmark (default: 100000)"
    )
    parser.add_argument(
        "--value-size",
        type=int,
        default=1024,
        help="Size of each value in bytes for synthetic mode (default: 1024)"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("KEY-VALUE DATABASE BENCHMARK - STUDY N°2")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Databases: {', '.join(args.db)}")
    
    if args.dataset:
        print(f"Datasets: {', '.join(args.dataset)}")
    else:
        print(f"Mode: Synthetic ({args.keys:,} keys, {args.value_size} bytes each)")
    print("="*70)
    
    results = {}
    
    if args.dataset:
        # Real dataset mode
        for db in args.db:
            for dataset in args.dataset:
                key = f"{db}_{dataset}"
                results[key] = run_dataset_benchmark(db, dataset)
    else:
        # Synthetic mode
        for db in args.db:
            results[db] = run_synthetic_benchmark(db, args.keys, args.value_size)
    
    # Save all metrics
    save_all_metrics(results)
    
    # Print comparison
    print_comparison(results, use_datasets=bool(args.dataset))
    
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()
