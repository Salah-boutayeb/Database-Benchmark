"""
RavenDB Benchmark Implementation.

Concrete implementation of DatabaseBenchmark for RavenDB using the official Python client.
"""
import json
import os
import pandas as pd
from ravendb import DocumentStore
from ravendb.serverwide.operations.common import CreateDatabaseOperation
from ravendb.serverwide.database_record import DatabaseRecord
from typing import Optional

from ..base import DatabaseBenchmark


class RavenBenchmark(DatabaseBenchmark):
    """RavenDB benchmark implementation using ravendb-python client."""

    def __init__(
        self,
        base_dir: str,
        url: str = "http://localhost:8080",
        db_name: str = "benchmark_db_oop",
        container_name: str = "benchmark_raven"
    ):
        super().__init__("RavenDB", container_name, base_dir)
        self.url = url
        self.database_name = db_name
        self.store: Optional[DocumentStore] = None

    def connect(self) -> None:
        """Establish connection to RavenDB and drop existing database for clean benchmark."""
        self.store = DocumentStore(urls=[self.url], database=self.database_name)
        self.store.initialize()
        
        # Drop existing database for clean benchmark
        try:
            from ravendb.serverwide.operations.common import DeleteDatabaseOperation
            self.store.maintenance.server.send(
                DeleteDatabaseOperation(self.database_name, hard_delete=True)
            )
            print(f"Dropped existing database: {self.database_name}")
        except Exception as e:
            if "does not exist" not in str(e).lower():
                print(f"Note: {e}")
        
        # Create fresh database
        try:
            record = DatabaseRecord(self.database_name)
            self.store.maintenance.server.send(CreateDatabaseOperation(record))
            print(f"Created database: {self.database_name}")
        except Exception as e:
            print(f"Warning creating DB: {e}")
        
        print(f"Connected to RavenDB database: {self.database_name}")

    def insert_data(self, file_path: str, collection_name: str, batch_size: int = 5000) -> int:
        """Insert data using RavenDB Bulk Insert."""
        total_count = 0
        
        if file_path.endswith('.json') or 'goodreads' in file_path:
            with open(file_path, 'r') as f:
                with self.store.bulk_insert() as bulk_insert:
                    for line in f:
                        try:
                            doc = json.loads(line)
                            if '_id' in doc:
                                del doc['_id']
                            bulk_insert.store(doc, metadata={"@collection": collection_name})
                            total_count += 1
                            if total_count % 50000 == 0:
                                print(f"  Progress: {total_count} documents inserted...")
                        except json.JSONDecodeError:
                            continue
        else:
            # CSV file handling
            with self.store.bulk_insert() as bulk_insert:
                for chunk in pd.read_csv(file_path, chunksize=batch_size, on_bad_lines='skip'):
                    chunk = chunk.where(pd.notnull(chunk), None)
                    records = chunk.to_dict(orient='records')
                    for r in records:
                        if '_id' in r:
                            del r['_id']
                        bulk_insert.store(r, metadata={"@collection": collection_name})
                        total_count += 1
                    if total_count % 50000 == 0:
                        print(f"  Progress: {total_count} documents inserted...")
        
        print(f"Inserted {total_count} documents into {collection_name}")
        
        # Create index for efficient querying after import
        self._create_index_for_collection(collection_name)
        
        return total_count

    def _create_index_for_collection(self, collection_name: str) -> None:
        """Create an index for the collection to enable efficient queries."""
        from ravendb.documents.indexes.definitions import IndexDefinition, IndexFieldOptions
        from ravendb.documents.operations.indexes import PutIndexesOperation
        
        # Define index based on collection
        if collection_name == 'amazon':
            index_name = f"Amazon/ByScore"
            index_def = IndexDefinition(
                name=index_name,
                maps={f"from doc in docs.{collection_name}s select new {{ doc.Score, doc.Summary }}"}
            )
        else:
            index_name = f"Goodreads/ByRating"
            index_def = IndexDefinition(
                name=index_name,
                maps={f"from doc in docs.{collection_name}s select new {{ doc.rating, doc.review_text }}"}
            )
        
        try:
            self.store.maintenance.send(PutIndexesOperation(index_def))
            print(f"  Created index: {index_name}")
            
            # Wait for index to be non-stale
            import time
            print(f"  Waiting for index to complete...")
            time.sleep(5)  # Give RavenDB time to index
        except Exception as e:
            print(f"  Note creating index: {e}")

    def read_data(self, collection_name: str) -> None:
        """Perform read operations on RavenDB collection with realistic queries."""
        with self.store.open_session() as session:
            # Read one document
            results = list(session.advanced.document_query(collection_name=collection_name).take(1))
            if results:
                print(f"  Read 1 document from {collection_name}")
            
            # Count matching documents (same as MongoDB/ArangoDB)
            # RavenDB needs to iterate to count since count_lazily requires index
            if collection_name == 'amazon':
                # Amazon: Score > 4 - use statistics from query
                query = (
                    session.advanced.document_query(collection_name=collection_name)
                    .where_greater_than("Score", 4)
                )
            else:
                # Goodreads: rating >= 3
                query = (
                    session.advanced.document_query(collection_name=collection_name)
                    .where_greater_than_or_equal("rating", 3)
                )
            
            # Execute query and get count from statistics
            # This scans all matching docs but only returns count
            count = 0
            for _ in query:
                count += 1
            
            print(f"  Found {count} documents matching query")

    def update_data(self, collection_name: str, limit: int = 10000) -> int:
        """Update documents in RavenDB collection using realistic queries."""
        updated_count = 0
        
        with self.store.open_session() as session:
            # Dataset-specific query for selecting documents to update
            # Note: RavenDB search() requires full-text indexes, so we use simpler filters
            if collection_name == 'amazon':
                # Amazon: Score > 4
                docs = list(
                    session.advanced.document_query(collection_name=collection_name)
                    .where_greater_than("Score", 4)
                    .take(limit)
                )
            else:
                # Goodreads: rating >= 3
                docs = list(
                    session.advanced.document_query(collection_name=collection_name)
                    .where_greater_than_or_equal("rating", 3)
                    .take(limit)
                )
            
            for doc in docs:
                if hasattr(doc, 'benchmark_updated'):
                    doc.benchmark_updated = True
                else:
                    doc['benchmark_updated'] = True
                updated_count += 1
            session.save_changes()
        
        print(f"  Updated {updated_count} documents")
        return updated_count

    def delete_data(self, collection_name: str) -> int:
        """Delete updated documents from RavenDB collection."""
        deleted_count = 0
        
        with self.store.open_session() as session:
            docs = list(
                session.advanced.document_query(collection_name=collection_name)
                .where_equals("benchmark_updated", True)
                .take(1000)
            )
            for doc in docs:
                session.delete(doc)
                deleted_count += 1
            session.save_changes()
        
        return deleted_count

    def export_data(self, collection_name: str) -> str:
        """Export RavenDB collection using streaming with fallback to pagination."""
        export_path = os.path.join(self.results_dir, f"export_{collection_name}_raven.json")
        
        total_exported = 0
        
        try:
            # Try streaming first (faster)
            with self.store.open_session() as session:
                query = session.advanced.document_query(collection_name=collection_name)
                stream_results = session.advanced.stream(query)
                
                with open(export_path, "w") as f:
                    for item in stream_results:
                        try:
                            doc = item.document
                            if '@metadata' in doc:
                                del doc['@metadata']
                            f.write(json.dumps(doc, default=str) + "\n")
                            total_exported += 1
                            if total_exported % 100000 == 0:
                                print(f"  Export progress: {total_exported} documents written...")
                        except Exception as e:
                            # Skip problematic documents
                            continue
            
            print(f"Exported {total_exported} documents to {export_path}")
            
        except Exception as stream_error:
            print(f"  Stream failed at {total_exported} docs, falling back to pagination...")
            
            # Fallback to pagination-based export
            page_size = 1000
            skip = total_exported  # Resume from where streaming failed
            
            with open(export_path, "a") as f:  # Append to what we already wrote
                while True:
                    with self.store.open_session() as session:
                        docs = list(
                            session.advanced.document_query(collection_name=collection_name)
                            .skip(skip)
                            .take(page_size)
                        )
                        
                        if not docs:
                            break
                        
                        for doc in docs:
                            try:
                                if hasattr(doc, '__dict__'):
                                    doc_dict = {k: v for k, v in doc.__dict__.items() 
                                               if not k.startswith('_')}
                                else:
                                    doc_dict = dict(doc) if isinstance(doc, dict) else {}
                                f.write(json.dumps(doc_dict, default=str) + "\n")
                                total_exported += 1
                            except Exception:
                                continue
                        
                        skip += len(docs)
                        
                        if total_exported % 100000 == 0:
                            print(f"  Export progress: {total_exported} documents written...")
                        
                        if len(docs) < page_size:
                            break
            
            print(f"Exported {total_exported} documents to {export_path}")
        
        return export_path

    def close(self) -> None:
        """Close RavenDB connection."""
        if self.store:
            self.store.close()
            print("RavenDB connection closed")
