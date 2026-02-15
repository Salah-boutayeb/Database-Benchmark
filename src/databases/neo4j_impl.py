
import logging
import time
from neo4j import GraphDatabase
from ..base import DatabaseBenchmark

class Neo4jBenchmark(DatabaseBenchmark):
    def __init__(self, base_dir: str, **kwargs):
        super().__init__("Neo4j", "benchmark_neo4j", base_dir)
        self.uri = "bolt://localhost:7687"
        self.auth = ("neo4j", "benchmark")
        self.driver = None

    def connect(self) -> None:
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
            # Verify connection
            self.driver.verify_connectivity()
            
            # Setup Constraints
            self._setup_schema()
            
        except Exception as e:
            logging.error(f"Error connecting to Neo4j: {e}")
            raise

    def _setup_schema(self):
        with self.driver.session() as session:
            # Create constraints/indexes
            # Drop previous formatting if needed? No, constraints are idempotent-ish or we catch error
            # Reset database for benchmark?
            session.run("MATCH (n) DETACH DELETE n") # DANGEROUS: Wipes DB. Good for benchmark.
            
            # User ID Constraint
            try:
                session.run("CREATE CONSTRAINT FOR (u:User) REQUIRE u.id IS UNIQUE")
            except Exception:
                pass # Already exists
            
            # Product ID Constraint
            try:
                session.run("CREATE CONSTRAINT FOR (p:Product) REQUIRE p.id IS UNIQUE")
            except Exception:
                pass

    def insert_data(self, file_path, collection, batch_size=1000, limit=None) -> int:
        count = 0
        import json
        import csv
        
        # We need to process Users, Products, and Reviews (Edges)
        # Strategy: 
        # 1. Iterate file, build lists of Users, Products, Reviews
        # 2. Batch insert Users (UNWIND)
        # 3. Batch insert Products (UNWIND)
        # 4. Batch insert Edges (UNWIND)
        
        # Note: In a real stream, we might do this in mixed batches, but for Neo4j UNWIND is efficient per type.
        # Given dataset size (1.85M reviews), holding all unique users/products in memory might be okay?
        # Amazon: 568k reviews. 
        # Goodreads: 1.85M reviews.
        # Users might be repeated. Products might be repeated.
        # To avoid OOM, we should process in chunks of raw reviews, and extract unique U/P from that chunk.
        
        nodes_users = set()
        nodes_products = set()
        edges_reviews = []
        
        is_csv = file_path.lower().endswith('.csv')
        
        # Optimized Strategy:
        # 1. Collect all data in memory (given dataset size fits in RAM)
        # 2. Batch Insert Unique Users
        # 3. Batch Insert Unique Products
        # 4. Batch Insert Edges (using MATCH only, knowing nodes exist)
        
        nodes_users = set()
        nodes_products = set()
        edges_reviews = []
        
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
                        rating = float(item.get('Score', 0) or 0)
                    else:
                        doc = json.loads(item)
                        user_id = doc.get('user_id', 'unknown')
                        product_id = doc.get('product_id', doc.get('book_id', 'unknown'))
                        rating = float(doc.get('rating', 0) or 0)
                    
                    nodes_users.add(user_id)
                    nodes_products.add(product_id)
                    edges_reviews.append({
                        'u': user_id, 
                        'p': product_id, 
                        'r': rating
                    })
                    count += 1
            
            logging.info(f"Collected {len(nodes_users)} Users, {len(nodes_products)} Products, {len(edges_reviews)} Edges.")
            
            with self.driver.session() as session:
                # 1. Users
                self._batch_insert_nodes(session, list(nodes_users), "User")
                logging.info("Inserted Users")
                
                # 2. Products
                self._batch_insert_nodes(session, list(nodes_products), "Product")
                logging.info("Inserted Products")
                
                # 3. Edges
                # Process edges in batches
                batch = []
                for i, edge in enumerate(edges_reviews):
                    batch.append(edge)
                    if len(batch) >= batch_size:
                        self._flush_edge_batch(session, batch)
                        batch = []
                        if i % 10000 == 0:
                             logging.info(f"Neo4j Processed {i} edges...")
                if batch:
                    self._flush_edge_batch(session, batch)
                    
        except Exception as e:
            logging.error(f"Error inserting data into Neo4j: {e}")
            
        return count

    def _batch_insert_nodes(self, session, nodes, label):
        # Insert nodes in batches
        batch_size = 5000
        batch = []
        query = f"UNWIND $batch as id MERGE (n:{label} {{id: id}})"
        
        for i, node_id in enumerate(nodes):
            batch.append(node_id)
            if len(batch) >= batch_size:
                session.run(query, batch=batch)
                batch = []
        if batch:
             session.run(query, batch=batch)

    def _flush_edge_batch(self, session, batch):
        # Edges: MATCH (u), (p) CREATE (u)-[r]->(p)
        # Since we know U and P exist (MERGE'd above), we can use MATCH which is fast with index.
        query = """
        UNWIND $batch AS row
        MATCH (u:User {id: row.u})
        MATCH (p:Product {id: row.p})
        MERGE (u)-[:REVIEWED {rating: row.r}]->(p)
        """
        session.run(query, batch=batch)

    def read_data(self, collection) -> None:
        pass

    def prepare_reads(self, file_path, num_samples=1000):
        import csv
        import json
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
        target_ids = self.prepare_reads(file_path, num_ops)
        if not target_ids:
            logging.warning("No IDs found for Neo4j read test")
            return
            
        # Budgeted Traversal Strategy (Matching OrientDB implementation)
        # Limit breadth at each step to prevent supernode explosion
        query = """
        MATCH (u:User {id: $uid})-[:REVIEWED]->(p:Product)
        WITH p LIMIT 50
        MATCH (p)<-[:REVIEWED]-(other:User)
        WITH other LIMIT 50
        MATCH (other)-[:REVIEWED]->(rec:Product)
        RETURN rec.id
        LIMIT 20
        """
        
        with self.driver.session() as session:
            for uid in target_ids:
                start_time = time.time()
                res = session.run(query, uid=uid).data() # Use data() to consume and get list
                logging.info(f"User {uid}: Found {len(res)} recommendations in {time.time() - start_time:.4f}s")

    def update_data(self, collection, limit=1000) -> int:
        return 0

    def delete_data(self, collection) -> int:
        return 0

    def export_data(self, collection) -> str:
        return ""

    def close(self) -> None:
        if self.driver:
            self.driver.close()
