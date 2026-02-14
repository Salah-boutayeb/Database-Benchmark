# Database Benchmarking Report

## Executive Summary

This report presents benchmark results comparing **5 databases** across two studies:

| Study                            | Databases                  | Dataset                    | Documents   |
| -------------------------------- | -------------------------- | -------------------------- | ----------- |
| **Study 1: Document DBs**  | MongoDB, ArangoDB, RavenDB | Amazon + Goodreads reviews | 568K + 2.3M |
| **Study 2: Key-Value DBs** | DynamoDB Local, Riak KV    | Amazon reviews             | 568K        |

---

## Study 1: Document Database Benchmark

### Databases Tested

- **MongoDB 7.0** - Leading document database
- **ArangoDB 3.12** - Multi-model database
- **RavenDB 6.0** - .NET-optimized document database

### Test Environment

- Docker containers on local machine
- Amazon reviews: 568,454 documents (367 MB)
- Goodreads reviews: 2,360,655 documents (2.3 GB)

---

### Results: Goodreads Dataset (2.36M documents)

| Operation        | MongoDB | ArangoDB | RavenDB | Winner                   |
| ---------------- | ------- | -------- | ------- | ------------------------ |
| **Import** | 31.05s  | 144.93s  | 130.39s | 🏆 MongoDB (4.7x faster) |
| **CRUD**   | 2.56s   | 14.58s   | 75.97s  | 🏆 MongoDB (5.7x faster) |
| **Export** | 29.17s  | 37.87s   | 89.08s  | 🏆 MongoDB (1.3x faster) |

### Results: Amazon Dataset (568K documents)

| Operation        | MongoDB | ArangoDB | RavenDB | Winner                   |
| ---------------- | ------- | -------- | ------- | ------------------------ |
| **Import** | 10.23s  | 29.32s   | 41.83s  | 🏆 MongoDB (2.9x faster) |
| **CRUD**   | 1.21s   | 3.41s    | 38.07s  | 🏆 MongoDB (2.8x faster) |
| **Export** | 5.15s   | 9.83s    | 24.95s  | 🏆 MongoDB (1.9x faster) |

### Resource Usage Comparison

| Database | Avg CPU % | Avg RAM (MB) | Peak RAM (MB) |
| -------- | --------- | ------------ | ------------- |
| MongoDB  | 40.5%     | 2,125        | 2,513         |
| ArangoDB | 74.1%     | 2,169        | 3,368         |
| RavenDB  | 81.6%     | 2,493        | 4,144         |

---

## Study 2: Key-Value Database Benchmark

### Databases Tested

- **DynamoDB Local** - AWS key-value store (local emulator)
- **Riak KV** - Distributed key-value database

### Test Environment

- Docker containers on local machine
- Amazon reviews: 568,454 documents stored as JSON bytes
- Data stored as: `key="amazon_N"` → `value=JSON_string`

---

### Results: Amazon Dataset (568K documents)

| Operation                  | DynamoDB | Riak KV  | Winner      | Speedup                |
| -------------------------- | -------- | -------- | ----------- | ---------------------- |
| **Insert**           | 113.7s   | 1,187.5s | 🏆 DynamoDB | **10.4x faster** |
| **Read (1000 docs)** | 1.07s    | 1.45s    | 🏆 DynamoDB | 1.4x faster            |
| **Export (full)**    | 633.2s   | 924.2s   | 🏆 DynamoDB | 1.5x faster            |

### Throughput Comparison

| Metric          | DynamoDB | Riak KV |
| --------------- | -------- | ------- |
| Insert docs/sec | 5,000    | 479     |
| Insert MB/sec   | 3.23     | 0.31    |

---

## Cross-Study Analysis: Document vs Key-Value

### Insert Performance (Amazon 568K docs)

| Rank | Database           | Time      | Type      |
| ---- | ------------------ | --------- | --------- |
| 1    | **MongoDB**  | 10.23s    | Document  |
| 2    | **ArangoDB** | 29.32s    | Document  |
| 3    | **RavenDB**  | 41.83s    | Document  |
| 4    | **DynamoDB** | 113.70s   | Key-Value |
| 5    | **Riak KV**  | 1,187.49s | Key-Value |

> **Note**: Document databases use optimized bulk insert APIs. Key-Value databases insert documents one-by-one or in small batches (25 items for DynamoDB).

---

## Key Findings

### 1. MongoDB Dominates Document Operations

- **Fastest** for import, CRUD, and export across all datasets
- **Lowest resource usage** among document databases
- Mature, optimized bulk operations

### 2. DynamoDB Leads Key-Value Performance

- **10x faster** than Riak for batch inserts
- Excellent point lookup performance (~1ms per document)
- AWS SDK well-optimized for batch operations

### 3. ArangoDB: Balanced Multi-Model

- Decent performance across all operations
- Multi-model flexibility (documents, graphs, key-value)
- Higher CPU usage than MongoDB

### 4. RavenDB: Slower but Feature-Rich

- Slowest in benchmarks due to REST API overhead
- Best suited for .NET environments
- ACID transactions and strong consistency

### 5. Riak KV: Distributed but Slow

- Designed for distributed clusters, not single-node
- Very slow single-node insert performance
- Required Docker configuration fixes (ulimits, volume cleanup)

---

## Technical Implementation

### Repository Structure

```
DB_benchmarking/
├── src/
│   ├── base/
│   │   ├── benchmark_base.py      # Document DB base class
│   │   ├── kv_benchmark_base.py   # Key-Value DB base class
│   │   └── resource_monitor.py    # Docker resource monitoring
│   └── databases/
│       ├── mongo_impl.py
│       ├── arango_impl.py
│       ├── raven_impl.py
│       ├── dynamodb_impl.py
│       └── riak_impl.py
├── data/
│   ├── amazon_reviews.csv         # 568K reviews
│   └── goodreads_reviews_*.json   # 2.36M reviews
├── results/
│   ├── all_metrics.json           # Document DB results
│   ├── all_kv_metrics_*.json      # Key-Value DB results
│   └── export_*.json              # Exported data
└── docker-compose.yml             # All database containers
```

### How to Run

```bash
# Start all databases
docker compose up -d

# Run Document DB benchmark
python main.py --db all --skip-cleanup

# Run Key-Value DB benchmark
python main_kv.py --db all --dataset amazon
```

---

## Recommendations

| Use Case                      | Recommended Database                |
| ----------------------------- | ----------------------------------- |
| General document storage      | **MongoDB**                   |
| Multi-model (docs + graphs)   | **ArangoDB**                  |
| .NET ecosystem                | **RavenDB**                   |
| AWS cloud-native key-value    | **DynamoDB**                  |
| High-availability distributed | **Riak KV** (in cluster mode) |

---

## Appendix: Raw Metrics

### Document Database Metrics (seconds)

| Database | Import GR | CRUD GR | Export GR | Import AM | CRUD AM | Export AM |
| -------- | --------- | ------- | --------- | --------- | ------- | --------- |
| MongoDB  | 31.05     | 2.56    | 29.17     | 10.23     | 1.21    | 5.15      |
| ArangoDB | 144.93    | 14.58   | 37.87     | 29.32     | 3.41    | 9.83      |
| RavenDB  | 130.39    | 75.97   | 89.08     | 41.83     | 38.07   | 24.95     |

*GR = Goodreads, AM = Amazon*

### Key-Value Database Metrics (seconds)

| Database | Insert  | Read (1K) | Export (Full) |
| -------- | ------- | --------- | ------------- |
| DynamoDB | 113.70  | 1.07      | 633.22        |
| Riak KV  | 1187.49 | 1.45      | 924.16        |
