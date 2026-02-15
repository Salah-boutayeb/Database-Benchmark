
import argparse
import logging
import os
import sys
from typing import List

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.base import DatabaseBenchmark
from src.databases.cassandra_impl import CassandraBenchmark
from src.databases.hbase_impl import HBaseBenchmark

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ColumnBenchmark")

DATASETS = {
    "amazon": "data/amazon_reviews.csv", # Need JSON conversion? Or reuse?
    "goodreads": "data/goodreads_reviews_mystery_thriller_crime.json"
}

# Assuming amazon_reviews is already converted to JSON in Study 1
# Check if json file exists, else use csv logic or expect json
AMAZON_JSON = "data/amazon_reviews.json" 

def main():
    parser = argparse.ArgumentParser(description="Column-Oriented Database Benchmark Runner (Study 3)")
    parser.add_argument("--db", nargs="+", choices=["cassandra", "hbase"], help="Databases to run (default: all)")
    parser.add_argument("--dataset", choices=["amazon", "goodreads", "all"], default="all", help="Dataset to use")
    parser.add_argument("--test", action="store_true", help="Run in test mode (small subset)")
    parser.add_argument("--skip-insert", action="store_true", help="Skip insertion phase (run only reads)")
    
    args = parser.parse_args()
    
    databases_to_run = args.db if args.db else ["cassandra", "hbase"]
    datasets_to_run = ["amazon", "goodreads"] if args.dataset == "all" else [args.dataset]
    
    # Base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Instantiate benchmarks
    benchmarks: List[DatabaseBenchmark] = []
    
    if "cassandra" in databases_to_run:
        benchmarks.append(CassandraBenchmark(base_dir))
    if "hbase" in databases_to_run:
        benchmarks.append(HBaseBenchmark(base_dir))
        
    for benchmark in benchmarks:
        logger.info(f"--- Starting Benchmark for {benchmark.db_name} ---")
        
        try:
            # Override datasets for test mode
            current_datasets = datasets_to_run
            
            benchmark.connect()
            
            # Execute per dataset
            for ds_name in current_datasets:
                file_path = DATASETS[ds_name]
                
                # Check file existence
                if not os.path.exists(file_path):
                    logger.warning(f"Dataset {file_path} not found. Skipping.")
                    continue
                    
                logger.info(f"Running on {ds_name}...")
                
                # Use insert_data as the main test for now (Study focus)
                # But we should use a template method like run_dataset_benchmark?
                # The Base class has run_full_benchmark. Let's use it or run manually if we want specificity.
                # Let's use specific calls to control the workflow for Column-Oriented (Batch Insert -> Scan)
                
                # 1. Insert
                if not args.skip_insert:
                    limit_count = 1000 if args.test else None
                    benchmark.measure_execution_time(
                        f"Import {ds_name}",
                        benchmark.insert_data, file_path, "reviews", batch_size=10, limit=limit_count
                    )
                
                # 2. Read / Scan
                if hasattr(benchmark, 'read_data_custom'):
                     benchmark.measure_execution_time(
                        f"Read {ds_name}",
                        benchmark.read_data_custom, file_path, num_ops=1000
                    )
                
            benchmark.save_results()
            benchmark.print_summary()
            benchmark.close()
            
        except Exception as e:
            logger.error(f"Benchmark failed for {benchmark.db_name}: {e}")
            # Continue to next DB
            
    logger.info("All benchmarks completed.")

if __name__ == "__main__":
    main()
