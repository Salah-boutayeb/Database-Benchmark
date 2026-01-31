#!/usr/bin/env python3
"""
Database Benchmarking Suite - Main Entry Point

This script orchestrates benchmarks across multiple NoSQL databases:
- MongoDB
- ArangoDB
- RavenDB

Uses the OOP architecture with ABC pattern for consistent, maintainable code.
"""
import os
import sys
import argparse
import json
import csv
from datetime import datetime
from typing import List, Type

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system env vars

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.databases import MongoBenchmark, ArangoBenchmark, RavenBenchmark
from src.base import DatabaseBenchmark


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')

# Datasets configuration: (file_path, collection_name, label)
DATASETS = [
    (os.path.join(DATA_DIR, 'goodreads_reviews_mystery_thriller_crime.json'), 'goodreads', 'Goodreads'),
    (os.path.join(DATA_DIR, 'amazon_reviews.csv'), 'amazon', 'Amazon'),
]

# Database configurations (credentials from environment variables)
DB_CONFIGS = {
    'mongodb': {
        'class': MongoBenchmark,
        'kwargs': {
            'base_dir': BASE_DIR,
            'uri': f"mongodb://{os.environ.get('MONGO_USER', 'admin')}:{os.environ.get('MONGO_PASSWORD', 'admin123')}@localhost:27017/",
            'db_name': 'benchmark_db',
            'container_name': 'mongodb'
        }
    },
    'arangodb': {
        'class': ArangoBenchmark,
        'kwargs': {
            'base_dir': BASE_DIR,
            'host': 'http://localhost:8529',
            'username': 'root',
            'password': os.environ.get('ARANGO_PASSWORD', 'password'),
            'db_name': 'benchmark_db',
            'container_name': 'benchmark_arango'
        }
    },
    'ravendb': {
        'class': RavenBenchmark,
        'kwargs': {
            'base_dir': BASE_DIR,
            'url': 'http://localhost:8080',
            'db_name': 'benchmark_db_oop',
            'container_name': 'benchmark_raven'
        }
    }
}


def run_single_benchmark(db_name: str) -> dict:
    """
    Run benchmark for a single database.
    
    Args:
        db_name: Database identifier (mongodb, arangodb, ravendb)
        
    Returns:
        Dictionary containing benchmark metrics
    """
    if db_name not in DB_CONFIGS:
        print(f"Unknown database: {db_name}")
        print(f"Available options: {list(DB_CONFIGS.keys())}")
        return {}
    
    config = DB_CONFIGS[db_name]
    benchmark_class = config['class']
    kwargs = config['kwargs']
    
    print(f"\n{'='*70}")
    print(f"STARTING {db_name.upper()} BENCHMARK")
    print(f"{'='*70}")
    
    benchmark = benchmark_class(**kwargs)
    benchmark.run_full_benchmark(DATASETS)
    
    return benchmark.metrics


def run_all_benchmarks() -> dict:
    """
    Run benchmarks for all configured databases.
    
    Returns:
        Dictionary mapping database names to their metrics
    """
    all_results = {}
    
    for db_name in DB_CONFIGS:
        try:
            metrics = run_single_benchmark(db_name)
            all_results[db_name] = metrics
        except Exception as e:
            print(f"\nError running {db_name} benchmark: {e}")
            import traceback
            traceback.print_exc()
            all_results[db_name] = {'error': str(e)}
    
    return all_results


def generate_comparative_report(results: dict) -> str:
    """
    Generate a comparative CSV report from all benchmark results.
    
    Args:
        results: Dictionary of results from all databases
        
    Returns:
        Path to the generated report
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(RESULTS_DIR, f'comparative_report_{timestamp}.csv')
    
    # Collect all unique operations
    all_operations = set()
    for db_metrics in results.values():
        if isinstance(db_metrics, dict) and 'error' not in db_metrics:
            all_operations.update(db_metrics.keys())
    
    # Write CSV
    with open(report_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['Operation']
        for db in results.keys():
            header.extend([f'{db}_duration_s', f'{db}_cpu_avg', f'{db}_ram_mb'])
        writer.writerow(header)
        
        # Data rows
        for op in sorted(all_operations):
            row = [op]
            for db, metrics in results.items():
                if isinstance(metrics, dict) and op in metrics:
                    data = metrics[op]
                    row.append(data.get('duration_seconds', 'N/A'))
                    row.append(data.get('resources', {}).get('container_cpu_avg', 'N/A'))
                    row.append(data.get('resources', {}).get('container_mem_avg_mb', 'N/A'))
                else:
                    row.extend(['N/A', 'N/A', 'N/A'])
            writer.writerow(row)
    
    print(f"\nComparative report saved to: {report_path}")
    return report_path


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Database Benchmarking Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run all benchmarks
  python main.py --db mongodb       # Run only MongoDB benchmark
  python main.py --db arangodb ravendb  # Run ArangoDB and RavenDB
  python main.py --list             # List available databases
        """
    )
    
    parser.add_argument(
        '--db', '--database',
        nargs='+',
        choices=list(DB_CONFIGS.keys()),
        help='Specific database(s) to benchmark'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available databases and exit'
    )
    
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip comparative report generation'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available databases:")
        for db in DB_CONFIGS:
            print(f"  - {db}")
        return
    
    print(f"\n{'='*70}")
    print("DATABASE BENCHMARKING SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Run benchmarks
    if args.db:
        results = {}
        for db in args.db:
            results[db] = run_single_benchmark(db)
    else:
        results = run_all_benchmarks()
    
    # Generate report
    if not args.no_report and any(
        isinstance(m, dict) and 'error' not in m 
        for m in results.values()
    ):
        generate_comparative_report(results)
    
    # Print final summary
    print(f"\n{'='*70}")
    print("BENCHMARK COMPLETE")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Save combined results
    combined_path = os.path.join(RESULTS_DIR, 'all_metrics.json')
    with open(combined_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"All metrics saved to: {combined_path}")


if __name__ == '__main__':
    main()
