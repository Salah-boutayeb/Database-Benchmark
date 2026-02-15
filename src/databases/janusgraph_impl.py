
import logging
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from ..base import DatabaseBenchmark

class JanusGraphBenchmark(DatabaseBenchmark):
    def __init__(self, base_dir: str, **kwargs):
        super().__init__("JanusGraph", "benchmark_janusgraph", base_dir)
        self.endpoint = 'ws://localhost:8182/gremlin'
        self.connection = None
        self.g = None

    def connect(self) -> None:
        try:
            self.connection = DriverRemoteConnection(self.endpoint, 'g')
            self.g = traversal().withRemote(self.connection)
            
            # Simple check
            # self.g.V().limit(1).toList()
            
            # Schema? JanusGraph often defaults to automatic schema creation.
            # Explicit schema usually requires Groovy script execution or Java API.
            # We will rely on automatic schema for this benchmark or submit a groovy script if needed.
            # For simplicity: dynamic schema.
            self._setup_schema()
            
        except Exception as e:
            logging.error(f"Error connecting to JanusGraph: {e}")
            raise

    def _setup_schema(self):
        # Create indexes for performance
        try:
            from gremlin_python.driver.client import Client
            client = Client(self.endpoint, 'g')
            
            # Groovy script to create schema
            script = """
            try {
                graph.tx().rollback()
                mgmt = graph.openManagement()
                
                boolean created = false
                if (!mgmt.containsPropertyKey('uid')) {
                    uid = mgmt.makePropertyKey('uid').dataType(String.class).make()
                    mgmt.buildIndex('byUid', Vertex.class).addKey(uid).buildCompositeIndex()
                    created = true
                }
                if (!mgmt.containsPropertyKey('pid')) {
                    pid = mgmt.makePropertyKey('pid').dataType(String.class).make()
                    mgmt.buildIndex('byPid', Vertex.class).addKey(pid).buildCompositeIndex()
                    created = true
                }
                
                mgmt.commit()
                if (created) {
                    // Wait for index?
                    Thread.sleep(1000)
                }
                'Schema Created'
            } catch (Exception e) {
                graph.tx().rollback()
                'Schema Error: ' + e.getMessage()
            }
            """
            res = client.submit(script).all().result()
            logging.info(f"JanusGraph Schema: {res}")
            client.close()
            
        except Exception as e:
            logging.error(f"Error setting up JanusGraph schema: {e}")

    def insert_data(self, file_path, collection, batch_size=1000, limit=None) -> int:
        count = 0
        import json
        import csv
        from gremlin_python.driver.client import Client
        
        # Multi-pass strategy:
        # 1. Collect unique Users and Products in memory
        # 2. Collect Edges
        # 3. Batch Insert Vertices
        # 4. Batch Insert Edges
        
        nodes_users = set()
        nodes_products = set()
        edges = []
        
        is_csv = file_path.lower().endswith('.csv')
        
        try:
            client = Client(self.endpoint, 'g')
            
            # PASS 1: Read and Collect
            with open(file_path, 'r') as f:
                if is_csv:
                    iterator = csv.DictReader(f)
                else:
                    iterator = f
                
                for item in iterator:
                    if limit and count >= limit:
                        break
                        
                    if is_csv:
                        user_id = item.get('UserId', 'unknown').replace("'", "")
                        product_id = item.get('ProductId', 'unknown').replace("'", "")
                        rating = item.get('Score', 0)
                    else:
                        doc = json.loads(item)
                        user_id = doc.get('user_id', 'unknown').replace("'", "")
                        product_id = doc.get('product_id', doc.get('book_id', 'unknown')).replace("'", "")
                        rating = doc.get('rating', 0)
                        
                    nodes_users.add(user_id)
                    nodes_products.add(product_id)
                    edges.append({'u': user_id, 'p': product_id, 'r': rating})
                    count += 1
            
            logging.info(f"Collected {len(nodes_users)} Users, {len(nodes_products)} Products, {len(edges)} Edges.")
            
            # PASS 2: Insert Users
            batch_script = ""
            b_cnt = 0
            for uid in nodes_users:
                # Check if exists? For benchmark, simplified: just insert.
                # Use strict addV. 
                # g.addV('User').property('uid', '...').next()
                # To be safe against rerun, we can drop all first? 
                # Or use fold().coalesce(unfold(), addV()) just for vertices is simpler/safer than edges.
                # Let's use coalesce for Vertices as it is standard.
                batch_script += f"g.V().has('User', 'uid', '{uid}').fold().coalesce(unfold(), addV('User').property('uid', '{uid}')).iterate()\n"
                b_cnt += 1
                if b_cnt >= 50:
                    client.submit(batch_script).all().result()
                    batch_script = ""
                    b_cnt = 0
            if batch_script:
                client.submit(batch_script).all().result()
                
            logging.info("Inserted Users.")
            
            # PASS 3: Insert Products
            batch_script = ""
            b_cnt = 0
            for pid in nodes_products:
                batch_script += f"g.V().has('Product', 'pid', '{pid}').fold().coalesce(unfold(), addV('Product').property('pid', '{pid}')).iterate()\n"
                b_cnt += 1
                if b_cnt >= 50:
                    client.submit(batch_script).all().result()
                    batch_script = ""
                    b_cnt = 0
            if batch_script:
                client.submit(batch_script).all().result()
                
            logging.info("Inserted Products.")
            
            # PASS 4: Insert Edges
            # Now we know vertices exist.
            # g.V().has('User','uid','u').as('u').V().has('Product','pid','p').addE('REVIEWED').from('u').to('p')...
            batch_script = ""
            b_cnt = 0
            for e in edges:
                # We need to find both nodes and add edge.
                # This traversal finds u, then finds p, then adds edge.
                # Note: this might be slow if indexes aren't perfect, but we rely on implicit index or scan (slow).
                # JanusGraph usually indexes primary keys if defined, but we defined none.
                # 'uid' and 'pid' are properties.
                # Without index, this is O(N) per edge.
                # Benchmarking might be limited by this. 
                # We should have created indexes in connect()! 
                
                cmd = f"g.V().has('User', 'uid', '{e['u']}').as('u').V().has('Product', 'pid', '{e['p']}').as('p').addE('REVIEWED').from('u').to('p').property('rating', {e['r']}).iterate()"
                batch_script += cmd + "\n"
                b_cnt += 1
                if b_cnt >= 50:
                    try:
                        client.submit(batch_script).all().result()
                    except Exception as err:
                        logging.error(f"Edge batch error: {err}")
                    batch_script = ""
                    b_cnt = 0
            if batch_script:
                client.submit(batch_script).all().result()
                
            logging.info("Inserted Edges.")
            
            client.close()

        except Exception as e:
            logging.error(f"Error inserting data into JanusGraph: {e}")
            
        return count

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
            logging.warning("No IDs found for JanusGraph read test")
            return
            
        import time
        
        # Budgeted Traversal Strategy (Matching OrientDB/Neo4j)
        # 1. User -> Out (Reviewed) limit 50
        # 2. Product -> In (Reviewed) limit 50 (Other Users)
        # 3. User -> Out (Reviewed) -> Product limit 20
        
        for uid in target_ids:
            try:
                start_time = time.time()
                # Recommendation Query
                res = self.g.V().has('User', 'uid', uid).out('REVIEWED').limit(50).in_('REVIEWED').limit(50).out('REVIEWED').dedup().limit(20).values('pid').toList()
                logging.info(f"User {uid}: Found {len(res)} recommendations in {time.time() - start_time:.4f}s")
            except Exception as e:
                logging.error(f"Read error for {uid}: {e}")

    def update_data(self, collection, limit=1000) -> int:
        return 0

    def delete_data(self, collection) -> int:
        return 0

    def export_data(self, collection) -> str:
        return ""

    def close(self) -> None:
        if self.connection:
            self.connection.close()
