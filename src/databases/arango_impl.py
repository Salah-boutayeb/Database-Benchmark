import json
import os
import pandas as pd
import math
from arango import ArangoClient
from typing import Optional, Any

from ..base import DatabaseBenchmark


class ArangoBenchmark(DatabaseBenchmark):

    def __init__(
        self,
        base_dir: str,
        host: str = "http://localhost:8529",
        username: str = "root",
        password: str = None,
        db_name: str = "benchmark_db",
        container_name: str = "benchmark_arango"
    ):
        super().__init__("ArangoDB", container_name, base_dir)
        self.host = host
        self.username = username
        # Use provided password or get from environment
        self.password = password or os.environ.get('ARANGO_PASSWORD', 'password')
        self.database_name = db_name
        self.client: Optional[ArangoClient] = None
        self.db = None

    def connect(self) -> None:
        """Establish connection to ArangoDB and drop existing database for clean benchmark."""
        self.client = ArangoClient(hosts=self.host)
        sys_db = self.client.db('_system', username=self.username, password=self.password)
        
        # Drop existing database for clean benchmark
        if sys_db.has_database(self.database_name):
            sys_db.delete_database(self.database_name)
            print(f"Dropped existing database: {self.database_name}")
        
        # Create fresh database
        sys_db.create_database(self.database_name)
        print(f"Created database: {self.database_name}")
        
        self.db = self.client.db(self.database_name, username=self.username, password=self.password)
        print(f"Connected to ArangoDB database: {self.database_name}")

    def _clean_document(self, doc: dict) -> dict:
        cleaned = {}
        for k, v in doc.items():
            if k == '_id':
                continue
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                cleaned[k] = None
            else:
                cleaned[k] = v
        return cleaned

    def insert_data(self, file_path: str, collection_name: str, batch_size: int = 10000) -> int:
        if self.db.has_collection(collection_name):
            self.db.delete_collection(collection_name)
        collection = self.db.create_collection(collection_name)
        
        total_count = 0
        
        if file_path.endswith('.json') or 'goodreads' in file_path:
            batch = []
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        doc = json.loads(line)
                        batch.append(self._clean_document(doc))
                        if len(batch) >= batch_size:
                            collection.insert_many(batch)
                            total_count += len(batch)
                            if total_count % 50000 == 0:
                                print(f"  Progress: {total_count} documents inserted...")
                            batch = []
                    except json.JSONDecodeError:
                        continue
                if batch:
                    collection.insert_many(batch)
                    total_count += len(batch)
        else:
            for chunk in pd.read_csv(file_path, chunksize=batch_size, on_bad_lines='skip'):
                chunk = chunk.where(pd.notnull(chunk), None)
                records = chunk.to_dict(orient='records')
                cleaned_records = [self._clean_document(r) for r in records]
                collection.insert_many(cleaned_records)
                total_count += len(records)
                if total_count % 50000 == 0:
                    print(f"  Progress: {total_count} documents inserted...")
        
        print(f"Inserted {total_count} documents into {collection_name}")
        return total_count

    def read_data(self, collection_name: str) -> None:
        """Perform read operations on ArangoDB collection with realistic queries."""
        # Read one document
        aql = f"FOR doc IN {collection_name} LIMIT 1 RETURN doc"
        cursor = self.db.aql.execute(aql)
        doc = next(cursor, None)
        
        # Dataset-specific realistic queries - use COUNT for fair comparison with MongoDB
        if collection_name == 'amazon':
            # Amazon: Score > 4 OR Summary contains 'good'
            aql_count = f"""
            RETURN LENGTH(
                FOR doc IN {collection_name}
                FILTER doc.Score > 4 OR CONTAINS(LOWER(doc.Summary), 'good')
                RETURN 1
            )
            """
        else:
            # Goodreads: rating >= 3 OR review_text contains keywords
            aql_count = f"""
            RETURN LENGTH(
                FOR doc IN {collection_name}
                FILTER doc.rating >= 3 OR 
                       CONTAINS(LOWER(doc.review_text), 'fantastic') OR
                       CONTAINS(LOWER(doc.review_text), 'suspense') OR
                       CONTAINS(LOWER(doc.review_text), 'story')
                RETURN 1
            )
            """
        
        # Execute count query
        cursor = self.db.aql.execute(aql_count, ttl=600)
        count = next(cursor, 0)
        print(f"  Found {count} documents matching query")

    def update_data(self, collection_name: str, limit: int = 10000) -> int:
        """Update documents in ArangoDB collection using realistic queries."""
        # Dataset-specific query for selecting documents to update
        if collection_name == 'amazon':
            # Amazon: Score > 4 OR Summary contains 'good'
            aql = f"""
            FOR doc IN {collection_name}
            FILTER doc.Score > 4 OR CONTAINS(LOWER(doc.Summary), 'good')
            LIMIT {limit}
            UPDATE doc WITH {{ benchmark_updated: true }} IN {collection_name}
            RETURN NEW
            """
        else:
            # Goodreads: rating >= 3 OR review_text contains keywords
            aql = f"""
            FOR doc IN {collection_name}
            FILTER doc.rating >= 3 OR 
                   CONTAINS(LOWER(doc.review_text), 'fantastic') OR
                   CONTAINS(LOWER(doc.review_text), 'suspense') OR
                   CONTAINS(LOWER(doc.review_text), 'story')
            LIMIT {limit}
            UPDATE doc WITH {{ benchmark_updated: true }} IN {collection_name}
            RETURN NEW
            """
        
        cursor = self.db.aql.execute(aql)
        updated = list(cursor)
        print(f"  Updated {len(updated)} documents")
        return len(updated)

    def delete_data(self, collection_name: str) -> int:
        """Delete updated documents from ArangoDB collection."""
        aql = f"""
        FOR doc IN {collection_name}
        FILTER doc.benchmark_updated == true
        REMOVE doc IN {collection_name}
        RETURN OLD
        """
        cursor = self.db.aql.execute(aql)
        deleted = list(cursor)
        return len(deleted)

    def export_data(self, collection_name: str) -> str:
        """Export ArangoDB collection using keyset pagination."""
        export_path = os.path.join(self.results_dir, f"export_{collection_name}_arango.json")
        
        total_exported = 0
        last_key = None
        page_size = 10000
        
        with open(export_path, "w") as f:
            while True:
                if last_key is None:
                    aql = f"FOR doc IN {collection_name} SORT doc._key LIMIT {page_size} RETURN doc"
                else:
                    aql = f"FOR doc IN {collection_name} FILTER doc._key > '{last_key}' SORT doc._key LIMIT {page_size} RETURN doc"
                
                cursor = self.db.aql.execute(aql)
                docs = list(cursor)
                
                if not docs:
                    break
                
                # Save last_key BEFORE deleting it from documents
                last_key = docs[-1].get('_key')
                
                for doc in docs:
                    if '_key' in doc:
                        del doc['_key']
                    if '_id' in doc:
                        del doc['_id']
                    if '_rev' in doc:
                        del doc['_rev']
                    f.write(json.dumps(doc) + "\n")
                    total_exported += 1
                
                if total_exported % 100000 == 0:
                    print(f"  Export progress: {total_exported} documents written...")
                
                if len(docs) < page_size:
                    break
        
        print(f"Exported {total_exported} documents to {export_path}")
        return export_path

    def close(self) -> None:
        """Close ArangoDB connection."""
        if self.client:
            self.client.close()
            print("ArangoDB connection closed")
