"""
MongoDB Benchmark Implementation.

Concrete implementation of DatabaseBenchmark for MongoDB using PyMongo.
"""
import json
import os
import pandas as pd
from pymongo import MongoClient
from typing import Optional

from ..base import DatabaseBenchmark


class MongoBenchmark(DatabaseBenchmark):
    """MongoDB benchmark implementation using PyMongo."""

    def __init__(
        self,
        base_dir: str,
        uri: str = None,
        db_name: str = "benchmark_db",
        container_name: str = "mongodb"
    ):
        super().__init__("MongoDB", container_name, base_dir)
        # Use provided URI or build from environment variables
        if uri is None:
            mongo_user = os.environ.get('MONGO_USER', 'admin')
            mongo_pass = os.environ.get('MONGO_PASSWORD', 'admin123')
            uri = f"mongodb://{mongo_user}:{mongo_pass}@localhost:27017/"
        self.uri = uri
        self.database_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> None:
        """Establish connection to MongoDB."""
        self.client = MongoClient(self.uri)
        self.db = self.client[self.database_name]
        print(f"Connected to MongoDB database: {self.database_name}")

    def insert_data(self, file_path: str, collection_name: str, batch_size: int = 10000) -> int:
        """Insert data from file into MongoDB collection."""
        collection = self.db[collection_name]
        collection.drop()  # Clear existing data
        
        total_count = 0
        
        if file_path.endswith('.json') or 'goodreads' in file_path:
            batch = []
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        batch.append(json.loads(line))
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
            # CSV file handling
            for chunk in pd.read_csv(file_path, chunksize=batch_size, on_bad_lines='skip'):
                chunk = chunk.where(pd.notnull(chunk), None)
                records = chunk.to_dict(orient='records')
                collection.insert_many(records)
                total_count += len(records)
                if total_count % 50000 == 0:
                    print(f"  Progress: {total_count} documents inserted...")
        
        print(f"Inserted {total_count} documents into {collection_name}")
        return total_count

    def read_data(self, collection_name: str) -> None:
        """Perform read operations on MongoDB collection with realistic queries."""
        collection = self.db[collection_name]
        
        # Read one document
        doc = collection.find_one()
        
        # Dataset-specific realistic queries
        if collection_name == 'amazon':
            # Amazon: Score > 4 OR Summary contains 'good'
            query = {
                "$or": [
                    {"Score": {"$gt": 4}},
                    {"Summary": {"$regex": "good", "$options": "i"}}
                ]
            }
        else:
            # Goodreads: rating >= 3 OR review_text contains keywords
            query = {
                "$or": [
                    {"rating": {"$gte": 3}},
                    {"review_text": {"$regex": "Fantastic|suspense|story", "$options": "i"}}
                ]
            }
        
        count = collection.count_documents(query)
        print(f"  Found {count} documents matching query")

    def update_data(self, collection_name: str, limit: int = 10000) -> int:
        """Update documents in MongoDB collection using realistic queries."""
        collection = self.db[collection_name]
        
        # Dataset-specific query for selecting documents to update
        if collection_name == 'amazon':
            # Amazon: Score > 4 OR Summary contains 'good'
            query = {
                "$or": [
                    {"Score": {"$gt": 4}},
                    {"Summary": {"$regex": "good", "$options": "i"}}
                ]
            }
        else:
            # Goodreads: rating >= 3 OR review_text contains keywords
            query = {
                "$or": [
                    {"rating": {"$gte": 3}},
                    {"review_text": {"$regex": "Fantastic|suspense|story", "$options": "i"}}
                ]
            }
        
        # Get IDs matching query (limited)
        ids = [d['_id'] for d in collection.find(query, {"_id": 1}).limit(limit)]
        
        # Update documents
        result = collection.update_many(
            {"_id": {"$in": ids}},
            {"$set": {"benchmark_updated": True}}
        )
        
        print(f"  Updated {result.modified_count} documents")
        return result.modified_count

    def delete_data(self, collection_name: str) -> int:
        """Delete updated documents from MongoDB collection."""
        collection = self.db[collection_name]
        
        result = collection.delete_many({"benchmark_updated": True})
        return result.deleted_count

    def export_data(self, collection_name: str) -> str:
        """Export MongoDB collection to JSON file."""
        collection = self.db[collection_name]
        export_path = os.path.join(self.results_dir, f"export_{collection_name}_mongo.json")
        
        total_exported = 0
        with open(export_path, "w") as f:
            for doc in collection.find():
                doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                f.write(json.dumps(doc) + "\n")
                total_exported += 1
                if total_exported % 100000 == 0:
                    print(f"  Export progress: {total_exported} documents written...")
        
        print(f"Exported {total_exported} documents to {export_path}")
        return export_path

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")
