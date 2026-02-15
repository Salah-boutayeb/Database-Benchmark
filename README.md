# 🔥 NoSQL Multi-Model Benchmark Suite

A comprehensive benchmarking framework for evaluating performance across four distinct NoSQL families: **Document**, **Key-Value**, **Column-Oriented**, and **Graph** databases.

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)

## 🎯 Overview

This project implements a modular, Object-Oriented benchmarking suite to compare the performance of various NoSQL solutions on real-world datasets (Amazon Reviews, Goodreads).

### Key Features
- **Polymorphic Architecture**: Common `DatabaseBenchmark` interface for all 11 database implementations.
- **Docker Integration**: Automated environment setup via `docker-compose`.
- **Real-Time Monitoring**: Prometheus and Grafana integration for resource tracking (CPU/RAM).
- **Automated Reporting**: Generation of JSON metrics and visualization charts.

---

## 📊 Databases Tested

| Family | Database | Driver | Implementation File |
| :--- | :--- | :--- | :--- |
| **Document** | **MongoDB** | `pymongo` | `mongo_impl.py` |
| | **ArangoDB** | `python-arango` | `arango_impl.py` |
| | **RavenDB** | `ravendb-python` | `raven_impl.py` |
| **Key-Value** | **DynamoDB** | `boto3` | `dynamodb_impl.py` |
| | **Riak KV** | `riak` | `riak_impl.py` |
| **Column** | **Cassandra** | `cassandra-driver` | `cassandra_impl.py` |
| | **HBase** | `happybase` | `hbase_impl.py` |
| **Graph** | **Neo4j** | `neo4j` | `neo4j_impl.py` |
| | **JanusGraph** | `gremlinpython` | `janusgraph_impl.py` |
| | **OrientDB** | `pyorient` | `orientdb_impl.py` |

---

## 📁 Project Structure

```
DB_benchmarking/
├── data/                        # Datasets (gitignored)
├── docs/                        # Project documentation
├── documentation_repports/      # Generated reports (MD/PDF) & Architecture
│   ├── ARCHITECTURE.md          # System Architecture & Config
│   ├── rapport_graphe.md        # Graph DB Study Report
│   └── images_graphe/           # Generated Charts
├── legacy/                      # Deprecated/Debug scripts
├── monitoring/                  # Prometheus & Grafana config
├── reports/                     # Report generation scripts
│   ├── generate_graph_charts.py # Graph DB Charts
│   └── generate_column_charts.py # Column DB Charts
├── results/                     # Raw benchmark metrics (JSON/CSV)
├── src/                         # Source Code
│   ├── base/                    # Abstract Base Classes
│   └── databases/               # Database Implementations
├── docker-compose.yml           # Container orchestration
├── main.py                      # Document DB Runner
├── main_kv.py                   # Key-Value DB Runner
├── main_column.py               # Column DB Runner
└── main_graph.py                # Graph DB Runner
```

---

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone repository
git clone <repo-url>
cd DB_benchmarking

# Install dependencies
pip install -r requirements.txt

# Start all database containers
docker compose up -d
```

### 2. Prepare Data
Download and place the following datasets in the `data/` directory:
- `amazon_reviews.csv`
- `goodreads_reviews_mystery_thriller_crime.json`

### 3. Run Benchmarks

#### Study 1: Document Databases
Comparing Import, CRUD, and Extract performance.
```bash
python main.py --db mongodb arangodb ravendb
```

#### Study 2: Key-Value Databases
Comparing Put/Get latency and throughput.
```bash
python main_kv.py --db dynamodb riak --dataset amazon
```

#### Study 3: Column-Oriented Databases
Comparing rigorous schema-based operations.
```bash
python main_column.py --db cassandra hbase --dataset all
```

#### Study 4: Graph Databases
Comparing Graph Construction (Insertion) and Traversal (Recommendation) performance.
```bash
python main_graph.py --db neo4j janusgraph orientdb --dataset goodreads
```
> **Note:** OrientDB insertion on Goodreads is significantly slower (~43 mins).

---

## 📈 Reports & Analysis

Detailed analysis and performance charts are available in the `documentation_repports/` directory.

- **Architecture:** [ARCHITECTURE.md](documentation_repports/ARCHITECTURE.md)
- **Graph Study:** [rapport_graphe.md](documentation_repports/rapport_graphe.md) (French)

### Generating Charts
You can regenerate charts from the latest result files:
```bash
python reports/generate_graph_charts.py
python reports/generate_column_charts.py
```

---

## 🛑 Cleanup

To stop and remove all containers (including data volumes):
```bash
docker compose down -v
```
