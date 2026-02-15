
import argparse
import logging
import os
import sys
from typing import List

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.base import DatabaseBenchmark
from src.databases.neo4j_impl import Neo4jBenchmark
from src.databases.orientdb_impl import OrientDBBenchmark
from src.databases.janusgraph_impl import JanusGraphBenchmark

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GraphBenchmark")

DATASETS = {
    "amazon": "data/amazon_reviews.csv",
    "goodreads": "data/goodreads_reviews_mystery_thriller_crime.json"
}

def main():
    parser = argparse.ArgumentParser(description="Run Graph DB Benchmarks")
    parser.add_argument("--db", type=str, choices=["neo4j", "orientdb", "janusgraph", "all"], default="all")
    parser.add_argument("--dataset", type=str, choices=["amazon", "goodreads", "all"], default="amazon")
    parser.add_argument("--test", action="store_true", help="Run on small subset")
    parser.add_argument("--skip-insert", action="store_true", help="Skip insertion phase")
    
    args = parser.parse_args()
    
    # Initialize benchmarks
    benchmarks: List[DatabaseBenchmark] = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.db in ["neo4j", "all"]:
        benchmarks.append(Neo4jBenchmark(base_dir))
    if args.db in ["orientdb", "all"]:
        benchmarks.append(OrientDBBenchmark(base_dir))
    if args.db in ["janusgraph", "all"]:
        benchmarks.append(JanusGraphBenchmark(base_dir))
        
    # Dataset selection
    selected_datasets = []
    if args.dataset == "all":
        selected_datasets = list(DATASETS.items())
    elif args.dataset in DATASETS:
        selected_datasets = [(args.dataset, DATASETS[args.dataset])]
        
    limit = 1000 if args.test else None
    
    for benchmark in benchmarks:
        logger.info(f"--- Starting Benchmark for {benchmark.db_name} ---")
        try:
            benchmark.connect()
            
            for ds_name, file_path in selected_datasets:
                logger.info(f"Running on {ds_name}...")
                
                # 1. Graph Creation (Insert)
                if not args.skip_insert:
                    benchmark.measure_execution_time(
                        f"Graph Creation {ds_name}",
                        benchmark.insert_data, file_path, "graph", batch_size=1000, limit=limit
                    )
                
                # 2. Recommendation Traversal (Read)
                num_ops = 100 if args.test else 20 # Traversal is expensive
                benchmark.measure_execution_time(
                    f"Recommendation {ds_name}",
                    benchmark.read_data_custom, file_path, num_ops
                )
                
            benchmark.save_results(f"_{ds_name}")
            
        except Exception as e:
            logger.error(f"Benchmark failed for {benchmark.db_name}: {e}")
        finally:
            benchmark.close()
            
    logger.info("All benchmarks completed.")

if __name__ == "__main__":
    main()
