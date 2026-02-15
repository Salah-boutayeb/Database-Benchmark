import logging
import pyorient
import time
from ..base import DatabaseBenchmark

class OrientDBBenchmark(DatabaseBenchmark):
    def __init__(self, base_dir: str, **kwargs):
        super().__init__("OrientDB", "benchmark_orientdb", base_dir)
        self.host = "localhost"
        self.port = 2424
        self.user = "root"
        self.password = "benchmark"
        self.client = None
        self.db_name = "benchmark_graph"

    def connect(self) -> None:
        try:
            self.client = pyorient.OrientDB(self.host, self.port)
            session_id = self.client.connect(self.user, self.password)
            
            # Create DB if not exists
            if not self.client.db_exists(self.db_name, pyorient.STORAGE_TYPE_PLOCAL):
                self.client.db_create(self.db_name, pyorient.DB_TYPE_GRAPH, pyorient.STORAGE_TYPE_PLOCAL)
            
            self.client.db_open(self.db_name, self.user, self.password)
            self._setup_schema()
            
        except Exception as e:
            logging.error(f"Error connecting to OrientDB: {e}")
            raise

    def _setup_schema(self):
        # Create Schema
        # Check if classes exist, if not create
        
        # Clean up for benchmark?
        # self.client.command("DELETE VERTEX V")
        # self.client.command("DELETE EDGE E") 
        # But this is slow for delete, better to recreate DB or just ignore for now if empty.
        
        classes = self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema)")
        class_names = [c.name for c in classes]
        
        if 'User' not in class_names:
            self.client.command("CREATE CLASS User EXTENDS V")
            self.client.command("CREATE PROPERTY User.id STRING")
            self.client.command("CREATE INDEX User.id UNIQUE")
            
        if 'Product' not in class_names:
            self.client.command("CREATE CLASS Product EXTENDS V")
            self.client.command("CREATE PROPERTY Product.id STRING")
            self.client.command("CREATE INDEX Product.id UNIQUE")
            
        if 'Reviewed' not in class_names:
            self.client.command("CREATE CLASS Reviewed EXTENDS E")
            self.client.command("CREATE PROPERTY Reviewed.rating FLOAT")

    def insert_data(self, file_path, collection, batch_size=1000, limit=None) -> int:
        count = 0
        import json
        import csv
        
        # Strategy:
        # OrientDB inserts are faster if we batch commands.
        # "BEGIN; INSERT INTO ...; INSERT INTO ...; COMMIT;"
        
        batch_cmds = []
        is_csv = file_path.lower().endswith('.csv')
        
        try:
            with open(file_path, 'r') as f:
                if is_csv:
                    iterator = csv.DictReader(f)
                else:
                    iterator = f
                
                for item in iterator:
                    if limit and count >= limit:
                        break
                        
                    if is_csv:
                        user_id = item.get('UserId', 'unknown')
                        product_id = item.get('ProductId', 'unknown')
                        rating = item.get('Score', 0)
                    else:
                        doc = json.loads(item)
                        user_id = doc.get('user_id', 'unknown')
                        product_id = doc.get('product_id', doc.get('book_id', 'unknown'))
                        rating = doc.get('rating', 0)

                    # We need to ensure U and P exist. MERGE-like behavior.
                    # UPSERT in OrientDB is "UPDATE ... UPSERT RETURN AFTER @rid WHERE ..."
                    # Or simpler: Just Insert and ignore errors, or assume clean DB?
                    # For performance, usually one does:
                    # UPDATE User SET id = '...' UPSERT WHERE id = '...'
                    # But edges need RIDs. 
                    
                    # Optimized approach:
                    # 1. Create Vertices (ignore duplicates/upsert)
                    # 2. Create Edge
                    
                    # Batch script
                    cmd = f"LET u = UPDATE User SET id = '{user_id}' UPSERT RETURN AFTER @rid WHERE id = '{user_id}';"
                    cmd += f"LET p = UPDATE Product SET id = '{product_id}' UPSERT RETURN AFTER @rid WHERE id = '{product_id}';"
                    cmd += f"CREATE EDGE Reviewed FROM $u TO $p SET rating = {rating};"
                    
                    batch_cmds.append(cmd)
                    
                    count += 1
                    
                    if len(batch_cmds) >= batch_size / 5: # Complex script, smaller batch
                        self._execute_batch(batch_cmds)
                        batch_cmds = []
                        if count % 1000 == 0:
                            logging.info(f"OrientDB Processed {count} items...")
                            
                if batch_cmds:
                    self._execute_batch(batch_cmds)

        except Exception as e:
            logging.error(f"Error inserting data into OrientDB: {e}")
            
        return count

    def _execute_batch(self, cmds):
        # Wrap in transaction
        script = "BEGIN;\n" + "\n".join(cmds) + "\nCOMMIT;"
        # pyorient batch/script execution
        self.client.batch(script)

    def read_data(self, collection) -> None:
        pass

    def prepare_reads(self, file_path, num_samples=1000):
        # Similar logic to Neo4j
        import csv
        import json
        ids = []
        is_csv = file_path.lower().endswith('.csv')
        try:
            with open(file_path, 'r') as f:
                iterator = csv.DictReader(f) if is_csv else f
                for i, item in enumerate(iterator):
                    if i % 1000 == 0: 
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
        target_ids = self.prepare_reads(file_path, num_ops)
        if not target_ids:
            logging.warning("No IDs found for OrientDB read test")
            return
            
        # Recommendation Query
        # Optimized with MATCH and TIMEOUT to prevent infinite hangs
        # MATCH {class: User, as: u, where: (id = ?)}.out("Reviewed").in("Reviewed").out("Reviewed"){as: rec, where: ($matched.u != $currentMatch)} RETURN count(*)
        
        for uid in target_ids:
            try:
                # Budgeted Traversal Strategy
                # Instead of a full depth-first traversal which explodes on supernodes,
                # we limit the breadth at each step.
                # 1. Get max 50 products reviewed by user
                # 2. Get max 50 other users who reviewed those products
                # 3. Get max 20 products from those users
                query = (
                    f"SELECT expand(out('Reviewed')) "
                    f"FROM ("
                    f"  SELECT expand(in('Reviewed')) "
                    f"  FROM ("
                    f"    SELECT expand(out('Reviewed')) "
                    f"    FROM User WHERE id = '{uid}' LIMIT 50"
                    f"  ) LIMIT 50"
                    f") LIMIT 20"
                )
                
                start_time = time.time()
                res = self.client.command(query)
                logging.info(f"User {uid}: Found {len(res)} recommendations in {time.time() - start_time:.4f}s")
                
            except Exception as e:
                logging.error(f"Error processing recommendation for user {uid}: {e}")
                try:
                    self.client.db_open(self.db_name, self.user, self.password)
                except:
                    pass

    def update_data(self, collection, limit=1000) -> int:
        return 0

    def delete_data(self, collection) -> int:
        return 0

    def export_data(self, collection) -> str:
        return ""

    def close(self) -> None:
        if self.client:
            self.client.close()
