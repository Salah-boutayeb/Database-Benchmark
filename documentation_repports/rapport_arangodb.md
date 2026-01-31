# Rapport Benchmark ArangoDB

**Date** : 31 Janvier 2026  
**Étude** : Benchmarking BDDs Orientées Documents (Framework OOP v2)

---

## 1. Configuration de Test

| Élément | Valeur |
|---------|--------|
| **Base de données** | ArangoDB 3.x (Docker) |
| **Conteneur** | `benchmark_arango` |
| **Client Python** | python-arango |
| **RAM limite** | 14.39 GiB |
| **Dataset 1** | Goodreads (1,849,236 docs, 1.75 GB) |
| **Dataset 2** | Amazon (568,454 docs, 287 MB) |

---

## 2. Architecture de Test

Le framework utilise des **requêtes AQL** (ArangoDB Query Language) :

### Requêtes CRUD Testées

| Dataset | Requête READ (COUNT) |
|---------|---------------------|
| Goodreads | `FILTER doc.rating >= 3 OR CONTAINS(LOWER(doc.review_text), 'fantastic')...` |
| Amazon | `FILTER doc.Score > 4 OR CONTAINS(LOWER(doc.Summary), 'good')` |

### Optimisations Appliquées

- **Nettoyage NaN** : Remplacement des `NaN` Pandas par `None` (VelocyPack)
- **Keyset Pagination** : Export par batch de 10K avec `_key > last_key`
- **TTL curseur** : 600s pour éviter les timeouts sur gros datasets

---

## 3. Résultats

### Performance par Opération

| Opération | Dataset | Durée (s) | CPU avg | CPU max | RAM avg (MB) | RAM max (MB) |
|-----------|---------|-----------|---------|---------|--------------|--------------|
| **Import** | Goodreads | 144.93 | 59.5% | 180.0% | 430 | 612 |
| **CRUD** | Goodreads | 14.58 | 51.1% | 101.1% | 1,619 | 2,324 |
| **Export** | Goodreads | 37.87 | 35.1% | 39.6% | 2,327 | 2,354 |
| **Import** | Amazon | 29.32 | 62.9% | 117.6% | 2,451 | 2,505 |
| **CRUD** | Amazon | 3.41 | 202.3% | 277.6% | 2,925 | 3,082 |
| **Export** | Amazon | 9.83 | 33.6% | 42.5% | 3,260 | 3,368 |

### Débit d'Ingestion

| Dataset | Documents | Durée | Débit |
|---------|-----------|-------|-------|
| Goodreads | 1,849,236 | 144.9s | **12,760 docs/s** |
| Amazon | 568,454 | 29.3s | **19,380 docs/s** |

### Totaux

| Métrique | Goodreads | Amazon | **Total** |
|----------|-----------|--------|-----------|
| Durée totale | 197.4s | 42.6s | **240.0s** |

---

## 4. Comparaison avec MongoDB

| Opération | MongoDB | ArangoDB | Ratio |
|-----------|---------|----------|-------|
| Import Goodreads | 31.0s | 144.9s | MongoDB **4.7x** plus rapide |
| CRUD Goodreads | 2.6s | 14.6s | MongoDB **5.6x** plus rapide |
| Export Goodreads | 29.2s | 37.9s | MongoDB **1.3x** plus rapide |
| Import Amazon | 10.2s | 29.3s | MongoDB **2.9x** plus rapide |
| CRUD Amazon | 1.2s | 3.4s | MongoDB **2.8x** plus rapide |
| RAM moyenne | 1-2 GB | 1-3 GB | Comparable |

---

## 5. Analyse

### Points Forts

✅ **Multi-modèle** : Support natif Graphes + Documents + Clé-Valeur  
✅ **AQL puissant** : Langage de requête expressif  
✅ **Parallélisation** : CPU max 200%+ sur CRUD Amazon  

### Points Faibles

❌ **Import 3-5x plus lent** que MongoDB  
❌ **Débit limité** : 12-19K docs/s vs 55-60K pour MongoDB  
❌ **Overhead batch** : Insertion document par document plus lente  

---

## 6. Conclusion

ArangoDB est **fonctionnel et stable** mais **significativement plus lent** que MongoDB pour les opérations documentaires pures.

| Critère | Performance |
|---------|-------------|
| Import massif | ⭐⭐ |
| Requêtes CRUD | ⭐⭐⭐ |
| Export | ⭐⭐⭐⭐ |
| Multi-modèle | ⭐⭐⭐⭐⭐ |

**Recommandé pour** : Applications nécessitant graphes + documents dans la même base.

---

*Fichier de métriques : `results/metrics_arangodb.json`*
