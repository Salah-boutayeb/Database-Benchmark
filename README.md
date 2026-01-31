# 🔥 NoSQL Document Database Benchmark

A comprehensive benchmarking framework for comparing **MongoDB**, **ArangoDB**, and **RavenDB** performance on real-world datasets.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

## 🎯 Features

- **OOP Architecture** - Clean, extensible design using Abstract Base Class pattern
- **Real-time Monitoring** - Prometheus + Grafana dashboards for live metrics
- **Container Metrics** - CPU, RAM, Network I/O via cAdvisor
- **CLI Interface** - Flexible command-line options
- **Unified Reports** - JSON + CSV output formats

## 📊 Databases Tested

| Database | Driver         | Container            |
| -------- | -------------- | -------------------- |
| MongoDB  | PyMongo        | `mongodb`          |
| ArangoDB | python-arango  | `benchmark_arango` |
| RavenDB  | ravendb-python | `benchmark_raven`  |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- ~10GB disk space for datasets

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/db-benchmark.git
cd db-benchmark

# Create environment file
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials (Optional)

Edit `.env` to customize database passwords:

```bash
MONGO_USER=admin
MONGO_PASSWORD=your_secure_password
ARANGO_PASSWORD=your_secure_password
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

### 3. Start Docker Services

```bash
docker compose up -d
```

This starts:

- 3 databases (MongoDB, ArangoDB, RavenDB)
- Prometheus + Grafana monitoring
- cAdvisor for container metrics

### 4. Add Your Data

Place your datasets in the `data/` directory:

```bash
data/
├── goodreads_reviews_mystery_thriller_crime.json  # JSON Lines format
└── amazon_reviews.csv                              # CSV format
```

### 5. Run Benchmarks

```bash
# All databases
python main.py

# Specific database(s)
python main.py --db mongodb
python main.py --db mongodb arangodb

# List available databases
python main.py --list
```

## 📈 Monitoring Dashboard

Access real-time metrics at:

| Service              | URL                   | Credentials   |
| -------------------- | --------------------- | ------------- |
| **Grafana**    | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | -             |
| **cAdvisor**   | http://localhost:8082 | -             |

## 📁 Project Structure

```
DB_benchmarking/
├── main.py                  # CLI entry point
├── src/
│   ├── base/
│   │   ├── benchmark_base.py    # Abstract Base Class
│   │   └── resource_monitor.py  # Docker metrics
│   └── databases/
│       ├── mongo_impl.py        # MongoDB implementation
│       ├── arango_impl.py       # ArangoDB implementation
│       └── raven_impl.py        # RavenDB implementation
├── monitoring/              # Prometheus + Grafana config
├── data/                    # Input datasets (gitignored)
├── results/                 # Output metrics (gitignored)
└── docs/                    # Documentation
```

## ⚙️ Operations Benchmarked

| Operation        | Description                  |
| ---------------- | ---------------------------- |
| **Import** | Bulk load entire dataset     |
| **Read**   | Complex queries with filters |
| **Update** | Modify up to 10K documents   |
| **Delete** | Remove modified documents    |
| **Export** | Write all data to JSON file  |

### Query Examples

**Amazon Dataset:**

```
Score > 4 OR Summary contains 'good'
```

**Goodreads Dataset:**

```
rating >= 3 OR review_text contains ['Fantastic', 'suspense', 'story']
```

## 📋 Metrics Collected

- **Duration** (seconds)
- **CPU Usage** (% average)
- **RAM Usage** (MB average)
- **Network I/O** (bytes)

## 🔧 Extending

Add a new database by:

1. Create `src/databases/newdb_impl.py`:

```python
from ..base import DatabaseBenchmark

class NewDBBenchmark(DatabaseBenchmark):
    def connect(self): ...
    def insert_data(self, file_path, collection, batch_size=10000): ...
    def read_data(self, collection): ...
    def update_data(self, collection, limit=10000): ...
    def delete_data(self, collection): ...
    def export_data(self, collection): ...
    def close(self): ...
```

2. Update `src/databases/__init__.py`
3. Add config to `main.py`

## 📝 Requirements

```txt
pandas>=1.5.0
pymongo>=4.0.0
python-arango>=7.0.0
ravendb>=5.2.0
python-dotenv>=1.0.0
```

## 🛑 Cleanup

```bash
docker compose down -v  # Remove containers and volumes
```
