# Rapport Benchmark RavenDB

**Étude** : Benchmarking BDDs Orientées Documents (Framework OOP v2)

---

## 1. Configuration de Test

| Élément                  | Valeur                              |
| -------------------------- | ----------------------------------- |
| **Base de données** | RavenDB 6.x (Docker)                |
| **Conteneur**        | `benchmark_raven`                 |
| **Client Python**    | ravendb-python                      |
| **API**              | HTTP REST + RQL                     |
| **Dataset 1**        | Goodreads (1,849,236 docs, 1.75 GB) |
| **Dataset 2**        | Amazon (568,454 docs, 287 MB)       |

---

## 2. Architecture de Test

### Spécificités RavenDB

- **Indexation automatique** : RavenDB crée des auto-indexes pour chaque requête
- **Index pré-créés** : Le framework crée les indexes après import pour éviter les timeouts
- **Bulk Insert** : API dédiée pour l'import massif
- **Fallback pagination** : Si le streaming échoue, bascule en pagination

### Requêtes CRUD Testées

| Dataset   | Requête READ                                | Index Créé           |
| --------- | -------------------------------------------- | ---------------------- |
| Goodreads | `where_greater_than_or_equal("rating", 3)` | `Goodreads/ByRating` |
| Amazon    | `where_greater_than("Score", 4)`           | `Amazon/ByScore`     |

---

## 3. Résultats

### Performance par Opération

| Opération       | Dataset   | Durée (s) | CPU avg | CPU max | RAM avg (MB) | RAM max (MB) |
| ---------------- | --------- | ---------- | ------- | ------- | ------------ | ------------ |
| **Import** | Goodreads | 130.39     | 61.2%   | 137.9%  | 2,818        | 3,415        |
| **CRUD**   | Goodreads | 75.97      | 102.6%  | 318.0%  | 3,175        | 4,144        |
| **Export** | Goodreads | 89.08      | 103.3%  | 165.3%  | 2,218        | 3,016        |
| **Import** | Amazon    | 41.83      | 54.5%   | 140.7%  | 2,485        | 2,854        |
| **CRUD**   | Amazon    | 38.07      | 83.2%   | 192.9%  | 2,234        | 2,799        |
| **Export** | Amazon    | 24.95      | 84.6%   | 155.7%  | 2,032        | 2,208        |

### Débit d'Ingestion

| Dataset   | Documents | Durée | Débit                  |
| --------- | --------- | ------ | ----------------------- |
| Goodreads | 1,849,236 | 130.4s | **14,180 docs/s** |
| Amazon    | 568,454   | 41.8s  | **13,600 docs/s** |

### Comptage Documents CRUD

| Dataset   | Documents matchés | Temps |
| --------- | ------------------ | ----- |
| Goodreads | 591,788            | 76s   |
| Amazon    | 363,122            | 38s   |

### Totaux

| Métrique     | Goodreads | Amazon | **Total**  |
| ------------- | --------- | ------ | ---------------- |
| Durée totale | 295.4s    | 104.9s | **400.3s** |

---

## 4. Comparaison avec MongoDB

| Opération       | MongoDB | RavenDB | Ratio                             |
| ---------------- | ------- | ------- | --------------------------------- |
| Import Goodreads | 31.0s   | 130.4s  | MongoDB**4.2x** plus rapide |
| CRUD Goodreads   | 2.6s    | 76.0s   | MongoDB**29x** plus rapide  |
| Export Goodreads | 29.2s   | 89.1s   | MongoDB**3.1x** plus rapide |
| Import Amazon    | 10.2s   | 41.8s   | MongoDB**4.1x** plus rapide |
| CRUD Amazon      | 1.2s    | 38.1s   | MongoDB**32x** plus rapide  |
| RAM moyenne      | 1-2 GB  | 2-3 GB  | MongoDB plus léger               |

---

## 5. Analyse

### Points Forts

✅ **ACID natif** : Transactions distribuées out-of-the-box
✅ **Subscriptions** : Notifications temps réel intégrées
✅ **API REST** : Simplicité d'intégration
✅ **.NET natif** : Excellente intégration écosystème Microsoft

### Points Faibles

❌ **CRUD très lent** : 29-32x plus lent que MongoDB (itération sans index efficace)
❌ **Import lent** : 4x plus lent que MongoDB malgré Bulk Insert
❌ **Dépendance indexes** : Performance dégradée sans indexes pré-créés
❌ **Streaming limité** : Fallback pagination sur gros volumes

### Particularité Observée

Le CRUD RavenDB itère sur tous les documents matchés pour compter (pas de `COUNT()` natif efficace), ce qui explique les temps importants sur 500K+ documents matchés.

---

## 6. Conclusion

RavenDB offre des **fonctionnalités avancées** (ACID, subscriptions) mais présente des **limitations de performance** significatives pour les opérations documentaires massives.

| Critère              | Performance |
| --------------------- | ----------- |
| Import massif         | ⭐⭐        |
| Requêtes CRUD        | ⭐          |
| Export                | ⭐⭐        |
| Fonctionnalités ACID | ⭐⭐⭐⭐⭐  |
| Écosystème .NET     | ⭐⭐⭐⭐⭐  |

**Recommandé pour** : Applications .NET nécessitant ACID et notifications temps réel.
