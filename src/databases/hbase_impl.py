
import logging
import happybase
from ..base import DatabaseBenchmark

class HBaseBenchmark(DatabaseBenchmark):
    def __init__(self, base_dir: str, **kwargs):
        super().__init__("HBase", "benchmark_hbase", base_dir)
        self.connection = None
        self.table = None
        self.table_name = "reviews"
        self.host = "localhost" # Docker mapped port
        self.port = 9090        # Thrift port

    def connect(self) -> None:
        try:
            # Connect to HBase Thrift server
            self.connection = happybase.Connection(self.host, port=self.port, autoconnect=False)
            self.connection.open()
            
            # Setup Schema
            self._setup_schema()
            
            self.table = self.connection.table(self.table_name)
        except Exception as e:
            logging.error(f"Error connecting to HBase: {e}")
            raise

    def _setup_schema(self):
        # Create table with column family 'cf'
        # If exists, disable and delete first for clean benchmark
        tables = self.connection.tables()
        if self.table_name.encode() in tables:
            self.connection.disable_table(self.table_name)
            self.connection.delete_table(self.table_name)
            
        self.connection.create_table(
            self.table_name,
            {'cf': dict()} # Single column family 'cf'
        )

    def insert_data(self, file_path, collection, batch_size=1000, limit=None) -> int:
        count = 0
        import json
        import csv
        from datetime import datetime
        
        # Batch insert
        batch = self.table.batch(batch_size=batch_size)
        
        try:
            is_csv = file_path.lower().endswith('.csv')
            
            with open(file_path, 'r') as f:
                if is_csv:
                    reader = csv.DictReader(f)
                    iterator = reader
                else:
                    iterator = f
                    
                for item in iterator:
                    if limit and count >= limit:
                        break

                    if is_csv:
                        # CSV Mapping
                        user_id = str(item.get('UserId', 'unknown'))
                        review_id = str(item.get('Id', 'unknown'))
                        product_id = str(item.get('ProductId', ''))
                        rating = str(item.get('Score', '0'))
                        summary = str(item.get('Summary', ''))
                        text = str(item.get('Text', ''))
                    else:
                        doc = json.loads(item)
                        user_id = str(doc.get('user_id', 'unknown'))
                        review_id = str(doc.get('review_id', 'unknown'))
                        product_id = str(doc.get('product_id', ''))
                        rating = str(doc.get('rating', '0'))
                        summary = str(doc.get('summary', ''))
                        text = str(doc.get('review_text', ''))
                    
                    # Simulated timestamp if missing
                    ts = int(datetime.now().timestamp() * 1000)
                    # Reverse timestamp for time series ordering (Newest first)
                    # RowKey: user_id : (MAX_LONG - timestamp) : review_id
                    row_key = f"{user_id}:{9999999999999 - ts}:{review_id}".encode()
                    
                    data = {
                        b'cf:product_id': product_id.encode(),
                        b'cf:rating': rating.encode(),
                        b'cf:summary': summary.encode(),
                        b'cf:text': text.encode()
                    }
                    
                    batch.put(row_key, data)
                    count += 1
            
            # Flush remaining
            batch.send()
            
        except Exception as e:
            logging.error(f"Error inserting data into HBase: {e}")
            # Ensure connection didn't drop
            
        return count

    def read_data(self, collection) -> None:
        # Abstract method implementation
        pass

    def prepare_reads(self, file_path, num_samples=1000):
        import csv
        import json
        # reuse helper logic or duplicate
        ids = []
        import json
        import csv
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
        target_ids = self.prepare_reads(file_path)
        if not target_ids:
            logging.warning("No IDs found for HBase read test")
            return
            
        for uid in target_ids:
            # Prefix scan for user: "user_id:"
            prefix = f"{uid}:".encode()
            # happybase scan returns a generator
            count = 0
            for key, data in self.table.scan(row_prefix=prefix):
                count += 1
                # consume generator


    def update_data(self, collection, limit=1000) -> int:
        return 0

    def delete_data(self, collection) -> int:
        # Disable/Drop table? Or modify schema?
        # Use batch delete for benchmark
        # self.connection.delete_table(self.table_name, disable=True)
        return 0

    def export_data(self, collection) -> str:
        # Scan full table
        return ""

    def close(self) -> None:
        if self.connection:
            self.connection.close()
