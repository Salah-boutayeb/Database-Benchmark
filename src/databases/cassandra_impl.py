
import logging
from cassandra.cluster import Cluster
from cassandra.query import BatchStatement, SimpleStatement
from cassandra import ConsistencyLevel
from ..base import DatabaseBenchmark

class CassandraBenchmark(DatabaseBenchmark):
    def __init__(self, base_dir: str, **kwargs):
        super().__init__("Cassandra", "benchmark_cassandra", base_dir)
        self.cluster = None
        self.session = None
        self.keyspace = "benchmark_ks"
        self.table = "reviews"

    def connect(self) -> None:
        try:
            self.cluster = Cluster(['localhost'], port=9042)
            self.session = self.cluster.connect()
            self._setup_schema()
        except Exception as e:
            logging.error(f"Error connecting to Cassandra: {e}")
            raise

    def _setup_schema(self):
        # Create Keyspace
        self.session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
        """)
        self.session.set_keyspace(self.keyspace)

        # Create Table
        # Modeling for:
        # 1. Point Read: Get review by review_id? Or by User?
        # 2. Key-Value style: id -> data
        # 3. Column style: user_id (Partition) + timestamp (Clustering) for Time Series
        # For fair comparison with HBase (RowKey often used for range scans), 
        # let's use user_id as partition key, and review_id as clustering key.
        
        # Drop if exists for clean state
        self.session.execute(f"DROP TABLE IF EXISTS {self.table}")
        
        self.session.execute(f"""
            CREATE TABLE {self.table} (
                user_id text,
                review_id text,
                product_id text,
                rating float,
                summary text,
                review_text text,
                timestamp timestamp,
                PRIMARY KEY (user_id, review_id)
            )
        """)

    def insert_data(self, file_path, collection_name, batch_size=50, limit=None):
        # Cassandra batch size is limited (warns > 5kb). 
        # We should use small batches or async inserts.
        # Batching partitions is good.
        # Here we use BatchStatement for simplicity but with smaller size than Mongo.
        
        count = 0
        import json
        import csv
        
        batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)
        
        # Prepared statement
        insert_stmt = self.session.prepare(f"""
            INSERT INTO {self.table} (user_id, review_id, product_id, rating, summary, review_text, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)
        
        # Load data logic (streaming)
        
        # Use existing load_dataset generator if available, but here we implement the loop
        
        try:
            is_csv = file_path.lower().endswith('.csv')
            
            with open(file_path, 'r') as f:
                if is_csv:
                    reader = csv.DictReader(f)
                    iterator = reader
                else:
                    iterator = f
                    
                current_batch_count = 0
                for item in iterator:
                    if limit and count >= limit:
                        break

                    if is_csv:
                        # CSV Mapping: Id,ProductId,UserId,ProfileName,HelpfulnessNumerator,HelpfulnessDenominator,Score,Time,Summary,Text
                        user_id = str(item.get('UserId', 'unknown'))
                        review_id = str(item.get('Id', 'unknown'))
                        product_id = str(item.get('ProductId', ''))
                        try:
                            rating = float(item.get('Score', 0.0))
                        except ValueError:
                            rating = 0.0
                        summary = str(item.get('Summary', ''))[:500]
                        text = str(item.get('Text', ''))[:1000]
                    else:
                        doc = json.loads(item)
                        user_id = str(doc.get('user_id', 'unknown'))
                        review_id = str(doc.get('review_id', 'unknown'))
                        product_id = str(doc.get('product_id', ''))
                        try:
                            rating = float(doc.get('rating', 0.0))
                        except ValueError:
                            rating = 0.0
                        summary = str(doc.get('summary', ''))[:500] 
                        text = str(doc.get('review_text', ''))[:1000]
                    
                    from datetime import datetime
                    ts = datetime.now() 
                    
                    batch.add(insert_stmt, (user_id, review_id, product_id, rating, summary, text, ts))
                    current_batch_count += 1
                    count += 1
                    
                    if current_batch_count >= batch_size:
                        self.session.execute(batch)
                        batch = BatchStatement(consistency_level=ConsistencyLevel.ONE)
                        current_batch_count = 0

                        
                # Flush remaining
                if current_batch_count > 0:
                    self.session.execute(batch)
                    
        except Exception as e:
            logging.error(f"Error inserting data into Cassandra: {e}")
            raise e
            
        return count

    def read_data(self, collection) -> None:
        # Abstract method
        pass

    def prepare_reads(self, file_path, num_samples=1000):
        import csv
        import json
        # Helper to get sample IDs
        ids = []
        is_csv = file_path.lower().endswith('.csv')
        try:
            with open(file_path, 'r') as f:
                iterator = csv.DictReader(f) if is_csv else f
                for i, item in enumerate(iterator):
                    if i % 1000 == 0: # Sample every 1000th
                        if is_csv:
                            uid = item.get('UserId')
                        else:
                            uid = json.loads(item).get('user_id')
                        if uid:
                            ids.append(uid)
                    if len(ids) >= num_samples:
                        break
        except Exception as e:
            logging.error(f"Error in prepare_reads: {e}")
        return ids

    def read_data_custom(self, file_path, num_ops=1000) -> None:
        # Custom method called by main_column.py
        target_ids = self.prepare_reads(file_path)
        if not target_ids:
            logging.warning("No IDs found for read test")
            return

        stmt = self.session.prepare(f"SELECT * FROM {self.table} WHERE user_id = ?")
        
        for uid in target_ids:
            self.session.execute(stmt, (uid,))


    def update_data(self, collection, limit=1000) -> int:
        return 0

    def delete_data(self, collection) -> int:
        return 0

    def export_data(self, collection) -> str:
        return ""

    def close(self) -> None:
        if self.cluster:
            self.cluster.shutdown()
