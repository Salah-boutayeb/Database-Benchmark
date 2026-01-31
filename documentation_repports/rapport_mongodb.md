# Rapport Benchmark MongoDB

**Étude** : Benchmarking BDDs Orientées Documents

## 1. Configuration de Test

| Élément                  | Valeur                              |
| -------------------------- | ----------------------------------- |
| **Base de données** | MongoDB 7.x (Docker)                |
| **Conteneur**        | `mongodb`                         |
| **Client Python**    | PyMongo                             |
| **RAM limite**       | 14.39 GiB                           |
| **Dataset 1**        | Goodreads (1,849,236 docs, 1.75 GB) |
| **Dataset 2**        | Amazon (568,454 docs, 287 MB)       |

---

## 2. Architecture de Test

Le framework utilise une architecture **OOP avec Abstract Base Class** :

- **DatabaseBenchmark** : Classe abstraite définissant le contrat
- **MongoBenchmark** : Implémentation spécifique MongoDB
- **DockerResourceMonitor** : Collecte métriques conteneur via `docker stats`

### Requêtes CRUD Testées

| Dataset   | Requête READ (count)                                              | Requête UPDATE                    |
| --------- | ------------------------------------------------------------------ | ---------------------------------- |
| Goodreads | `rating >= 3 OR review_text contains 'Fantastic\|suspense\|story'` | Ajoute `benchmark_updated: true` |
| Amazon    | `Score > 4 OR Summary contains 'good'`                           | Ajoute `benchmark_updated: true` |

---

## 3. Résultats

### Performance par Opération

| Opération       | Dataset   | Durée (s)      | CPU avg | CPU max | RAM avg (MB) | RAM max (MB) |
| ---------------- | --------- | --------------- | ------- | ------- | ------------ | ------------ |
| **Import** | Goodreads | **31.05** | 64.2%   | 106.7%  | 1,078        | 2,031        |
| **CRUD**   | Goodreads | **2.56**  | 53.4%   | 100.1%  | 2,173        | 2,185        |
| **Export** | Goodreads | 29.17           | 9.1%    | 20.6%   | 2,189        | 2,198        |
| **Import** | Amazon    | **10.23** | 37.5%   | 65.2%   | 2,327        | 2,473        |
| **CRUD**   | Amazon    | **1.21**  | 71.4%   | 71.4%   | 2,473        | 2,473        |
| **Export** | Amazon    | 5.15            | 7.1%    | 8.0%    | 2,512        | 2,513        |

### Débit d'Ingestion

| Dataset   | Documents | Durée | Débit                  |
| --------- | --------- | ------ | ----------------------- |
| Goodreads | 1,849,236 | 31.0s  | **59,630 docs/s** |
| Amazon    | 568,454   | 10.2s  | **55,580 docs/s** |

### Totaux

| Métrique     | Goodreads | Amazon  | **Total**     |
| ------------- | --------- | ------- | ------------------- |
| Durée totale | 62.8s     | 16.6s   | **79.4s**     |
| Documents     | 1,849,236 | 568,454 | **2,417,690** |

---

## 4. Analyse

### Points Forts

✅ **Import ultra-rapide** : ~55-60K documents/seconde en batch de 10,000
✅ **CRUD efficace** : Count de 1.8M docs avec filtre complexe en 2.5s
✅ **Faible consommation RAM** : ~1-2 GB (le plus bas des 3 bases)
✅ **Parallélisation** : CPU max 100%+ indique utilisation multi-core

### Observations

- **Export I/O bound** : CPU 7-9% indique que l'écriture disque est le goulot d'étranglement
- **RAM stable** : Pic à 2.5 GB, reste stable après chargement initial
- **Requêtes regex** : MongoDB gère les $regex sans index avec performance acceptable

---

## 5. Conclusion

MongoDB démontre d'**excellentes performances** pour toutes les opérations documentaires :

| Critère         | Performance |
| ---------------- | ----------- |
| Import massif    | ⭐⭐⭐⭐⭐  |
| Requêtes CRUD   | ⭐⭐⭐⭐⭐  |
| Export           | ⭐⭐⭐⭐    |
| Consommation RAM | ⭐⭐⭐⭐⭐  |

**MongoDB est la référence de ce benchmark** avec les meilleures performances sur tous les critères.
