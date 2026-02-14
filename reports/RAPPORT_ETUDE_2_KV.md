# Étude n°2 : Benchmark des Bases de Données Clé-Valeur

## Rapport Complet

---

## 1. Introduction

### 1.1 Contexte

Cette étude compare les performances de deux bases de données clé-valeur populaires dans un contexte de stockage et de récupération de données volumineuses. Les bases de données clé-valeur sont optimisées pour des opérations simples de type PUT/GET avec des temps de réponse minimaux.

### 1.2 Objectifs

- Évaluer les performances d'insertion massive de données
- Mesurer la vitesse de lecture aléatoire
- Comparer les temps d'exportation complète
- Identifier les forces et faiblesses de chaque solution

### 1.3 Bases de Données Testées

| Base de Données         | Version   | Type                   | Éditeur            |
| ------------------------ | --------- | ---------------------- | ------------------- |
| **DynamoDB Local** | Dernière | Clé-Valeur            | Amazon Web Services |
| **Riak KV**        | Dernière | Clé-Valeur Distribué | Basho Technologies  |

---

## 2. Environnement de Test

### 2.1 Infrastructure

- **Conteneurisation** : Docker avec Docker Compose
- **Système d'exploitation** : Linux
- **Configuration mémoire** :
  - DynamoDB : 2 Go heap JVM, 4 Go limite conteneur
  - Riak : ulimits nofile=65536, WAIT_FOR_ERLANG=120

### 2.2 Dataset Utilisé

| Caractéristique                      | Valeur                                     |
| ------------------------------------- | ------------------------------------------ |
| **Source**                      | Amazon Reviews (avis produits)             |
| **Nombre de documents**         | 568 454                                    |
| **Taille totale**               | 367,1 Mo                                   |
| **Taille moyenne par document** | 677 octets                                 |
| **Format de stockage**          | JSON sérialisé en chaîne de caractères |

### 2.3 Structure des Données

Chaque document est stocké comme suit :

- **Clé** : `amazon_<index>` (ex: `amazon_0`, `amazon_1`, ...)
- **Valeur** : Document JSON complet sous forme de chaîne

Exemple de document :

```json
{
  "Id": 47993,
  "ProductId": "B004SRH2B6",
  "UserId": "A3QG30LI3N9MZ6",
  "ProfileName": "Nandita Das",
  "Score": 2,
  "Summary": "Product is ok...",
  "Text": "Coconut water tastes..."
}
```

---

## 3. Méthodologie

### 3.1 Opérations Testées

| Opération       | Description                                            | Métrique                     |
| ---------------- | ------------------------------------------------------ | ----------------------------- |
| **INSERT** | Insertion par lots de tous les documents               | Temps total + débit (docs/s) |
| **READ**   | Lecture aléatoire de 1000 documents                   | Temps total                   |
| **EXPORT** | Export complet de tous les documents vers fichier JSON | Temps total                   |

### 3.2 Protocole de Test

1. **Nettoyage** : Suppression et recréation de la table/bucket
2. **Insertion** : Insertion par lots (25 documents par batch pour DynamoDB)
3. **Comptage** : Vérification du nombre de documents insérés
4. **Lecture** : Sélection aléatoire et lecture de 1000 documents
5. **Export** : Récupération et écriture de tous les documents dans un fichier JSON

### 3.3 Configuration Docker

```yaml
# DynamoDB Local
dynamodb-local:
  image: amazon/dynamodb-local:latest
  command: "-jar DynamoDBLocal.jar -sharedDb -inMemory"
  environment:
    JAVA_OPTS: "-Xmx2g -Xms512m"
  mem_limit: 4G
  ports:
    - "8000:8000"

# Riak KV
riak:
  image: basho/riak-kv:latest
  environment:
    - CLUSTER_NAME=riakts
    - WAIT_FOR_ERLANG=120
  ulimits:
    nofile:
      soft: 65536
      hard: 65536
  ports:
    - "8087:8087"
    - "8098:8098"
```

---

## 4. Résultats

### 4.1 Tableau Comparatif Global

| Opération                 | DynamoDB Local | Riak KV    | Gagnant     | Ratio                       |
| -------------------------- | -------------- | ---------- | ----------- | --------------------------- |
| **INSERT**           | 113,70 s       | 1 187,49 s | 🏆 DynamoDB | **10,4x plus rapide** |
| **READ** (1000 docs) | 1,07 s         | 1,45 s     | 🏆 DynamoDB | 1,4x plus rapide            |
| **EXPORT** (complet) | 633,22 s       | 924,16 s   | 🏆 DynamoDB | 1,5x plus rapide            |

### 4.2 Métriques de Débit

| Métrique                                 | DynamoDB Local | Riak KV |
| ----------------------------------------- | -------------- | ------- |
| **Documents insérés par seconde** | 4 999,59       | 478,70  |
| **Débit d'insertion (Mo/s)**       | 3,23           | 0,31    |
| **Temps moyen par document**        | 0,20 ms        | 2,09 ms |

### 4.3 Détail des Résultats

#### 4.3.1 DynamoDB Local

| Opération | Durée      | Observations                        |
| ---------- | ----------- | ----------------------------------- |
| INSERT     | 113,70 s    | Insertion fluide par lots de 25     |
| COUNT      | Instantané | Utilisation du compteur d'insertion |
| READ       | 1,07 s      | 1000 docs en ~1 ms chacun           |
| EXPORT     | 633,22 s    | Export complet vers JSON            |

**Fichier de sortie** : `results/export_kv_dynamodb-local_amazon.json`

#### 4.3.2 Riak KV

| Opération | Durée      | Observations                           |
| ---------- | ----------- | -------------------------------------- |
| INSERT     | 1 187,49 s  | ~20 min, insertion séquentielle lente |
| COUNT      | Instantané | Utilisation du compteur d'insertion    |
| READ       | 1,45 s      | Performance comparable à DynamoDB     |
| EXPORT     | 924,16 s    | Plus lent malgré même principe       |

**Fichier de sortie** : `results/export_kv_benchmark_riak_amazon.json`

---

## 5. Analyse des Résultats

### 5.1 Performance d'Insertion

**DynamoDB surpasse largement Riak** avec un ratio de 10,4x sur les insertions :

| Facteur              | DynamoDB                | Riak               |
| -------------------- | ----------------------- | ------------------ |
| API batch native     | ✅ Oui (25 items/batch) | ❌ Non             |
| Mode in-memory       | ✅ Configuré           | ❌ Non disponible  |
| Optimisation réseau | ✅ SDK AWS optimisé    | ⚠️ API HTTP REST |

### 5.2 Performance de Lecture

Les deux bases affichent des **performances similaires** pour les lectures ponctuelles :

- DynamoDB : ~1 ms par document
- Riak : ~1,5 ms par document

Cela confirme que les bases clé-valeur excellent pour les **lookups par clé unique**.

### 5.3 Performance d'Export

L'export nécessite de :

1. Récupérer chaque clé
2. Lire la valeur associée
3. Écrire dans un fichier

DynamoDB maintient son avantage grâce à des opérations GET plus rapides.

### 5.4 Problèmes Rencontrés

#### Riak KV

- **Problème** : Le conteneur ne démarrait pas (node not responding to pings)
- **Cause** : ulimit trop bas (1024 vs 65536 recommandé), volume de données corrompu
- **Solution** :

  ```yaml
  ulimits:
    nofile: 65536
  environment:
    - WAIT_FOR_ERLANG=120
  ```

  + Suppression du volume Docker

#### DynamoDB Local

- **Problème** : Crash OOM lors du COUNT
- **Cause** : Scan complet de table trop gourmand en mémoire
- **Solution** : Utilisation du compteur d'insertion au lieu du scan

---

## 6. Limites de l'Étude

### 6.1 Contexte Local vs Production

| Aspect   | Test Local       | Production              |
| -------- | ---------------- | ----------------------- |
| DynamoDB | Émulateur local | Service AWS managé     |
| Riak     | Nœud unique     | Cluster distribué      |
| Réseau  | Localhost        | Latence réseau réelle |

### 6.2 Facteurs Non Mesurés

- Haute disponibilité et réplication
- Comportement sous charge concurrente
- Coût d'exploitation
- Consistance des données

---

## 7. Conclusions

### 7.1 Synthèse

| Critère                            | Recommandation |
| ----------------------------------- | -------------- |
| **Performance pure**          | DynamoDB Local |
| **Facilité de déploiement** | DynamoDB Local |
| **Distribution multi-nœuds** | Riak KV        |
| **Intégration AWS**          | DynamoDB       |

### 7.2 Cas d'Usage Recommandés

| Base de Données   | Cas d'Usage Idéal                                                        |
| ------------------ | ------------------------------------------------------------------------- |
| **DynamoDB** | Applications serverless AWS, APIs haute performance, cache de session     |
| **Riak KV**  | Systèmes distribués haute disponibilité, stockage géo-répliqué, IoT |

### 7.3 Verdict Final

**DynamoDB Local** domine cette étude avec des performances **10x supérieures** sur les insertions et un avantage constant sur toutes les opérations. Cependant, Riak KV est conçu pour des **déploiements distribués** où sa force réside dans la tolérance aux pannes et la réplication, aspects non testés dans cette étude mono-nœud.

---
