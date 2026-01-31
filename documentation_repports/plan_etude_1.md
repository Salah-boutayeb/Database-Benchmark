# Plan de l'Étude 1 : Benchmarking BDDs Orientées Documents

## 1. Objectif
Comparer les performances de trois bases de données NoSQL orientées documents :
- **MongoDB**
- **ArangoDB**
- **RavenDB**

Sur deux jeux de données :
1. **Amazon Reviews** (~568K documents)
2. **Goodreads Reviews** (~1.8M documents)

## 2. Architecture Technique

### Infrastructure Docker
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│  Databases:                  Monitoring:                     │
│  ├── mongodb (:27017)        ├── prometheus (:9090)          │
│  ├── benchmark_arango(:8529) ├── grafana (:3000)             │
│  └── benchmark_raven (:8080) ├── cadvisor (:8082)            │
│                              ├── node-exporter (:9100)       │
│  Web UIs:                    └── mongodb-exporter (:9216)    │
│  └── mongo-express (:8081)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Structure du projet (Architecture OOP)
```
DB_benchmarking/
├── docker-compose.yml          # Services Docker (DBs + Monitoring)
├── main.py                     # CLI principal (argparse)
├── src/
│   ├── base/
│   │   ├── benchmark_base.py   # Abstract Base Class
│   │   └── resource_monitor.py # Monitoring CPU/RAM via docker stats
│   └── databases/
│       ├── mongo_impl.py       # Implémentation MongoDB
│       ├── arango_impl.py      # Implémentation ArangoDB
│       └── raven_impl.py       # Implémentation RavenDB
├── monitoring/
│   ├── prometheus.yml          # Configuration Prometheus
│   └── grafana/                # Dashboards Grafana
├── data/                       # Datasets (ignoré dans git)
├── results/                    # Résultats (JSON/CSV)
└── docs/                       # Documentation
```

## 3. Méthodologie

### A. Acquisition des Données
| Dataset | Source | Format | Taille |
|---------|--------|--------|--------|
| Amazon Reviews | Fichier local | JSON Lines | ~568K docs |
| Goodreads Reviews | Fichier local | JSON Lines | ~1.8M docs |

### B. Opérations Testées (KPIs)

#### Métriques collectées
- **Temps d'exécution** (secondes)
- **CPU** (% moyen via cAdvisor/docker stats)
- **RAM** (MB moyen)

#### Tests réalisés

| Opération | Description | Volume |
|-----------|-------------|--------|
| **Import** | Chargement massif (bulk insert) | Dataset complet |
| **Read** | Requêtes réalistes (voir ci-dessous) | Tous les docs matchants |
| **Update** | Mise à jour conditionnelle | 10,000 docs max |
| **Delete** | Suppression des docs modifiés | Tous les docs marqués |
| **Export** | Export complet vers JSON | Dataset complet |

### C. Requêtes CRUD Réalistes

#### Amazon Collection
```
Score > 4 OR Summary contient 'good'
```

#### Goodreads Collection
```
rating >= 3 OR review_text contient ['Fantastic', 'suspense', 'story']
```

> **Note**: RavenDB utilise des filtres numériques uniquement (Score > 4, rating >= 3) car la recherche full-text nécessite des index spécifiques.

## 4. Monitoring Temps Réel

### Stack Prometheus + Grafana
- **Prometheus**: Collecte des métriques toutes les 15s
- **Grafana**: Dashboard "Database Benchmark" avec :
  - CPU par conteneur
  - RAM par conteneur
  - I/O réseau
  - Opérations MongoDB/sec

### Accès
| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |

## 5. Exécution

### Démarrer l'environnement
```bash
cd DB_benchmarking
docker compose up -d
```

### Lancer les benchmarks
```bash
# Toutes les BDDs
python main.py

# Une seule BDD
python main.py --db mongodb

# Plusieurs BDDs
python main.py --db mongodb arangodb
```

## 6. Pré-requis
- Docker & Docker Compose
- Python 3.9+
- Bibliothèques : `pymongo`, `python-arango`, `ravendb`, `pandas`
