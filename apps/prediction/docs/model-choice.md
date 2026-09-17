# Choix du modèle : RandomForestRegressor

Ce document explique pourquoi le service prediction utilise un
`RandomForestRegressor` (scikit-learn) en phase 1, et quelles alternatives
sont envisageables ensuite.

## Problème formulé

**Régression** : prédire une valeur continue `consumption_kwh` (kWh) à partir de :

| Feature | Type | Rôle |
|---|---|---|
| `site_id` | Catégorielle | Profil de consommation propre à chaque site |
| `hour` | Numérique | Pattern horaire (matin, soir…) |
| `minute` | Numérique | Granularité intra-horaire |

Ce n'est pas une prévision de série temporelle pure (type ARIMA ou Prophet) :
on modélise une relation **tabulaire** site + moment → consommation.

## Pourquoi Random Forest

### Données tabulaires mixtes

Le pipeline encode `site_id` en one-hot et laisse passer `hour` / `minute`
telles quelles. Un Random Forest gère naturellement :

- des variables **catégorielles** (chaque site peut avoir un niveau différent) ;
- des relations **non linéaires** (pics à certaines heures, interactions site × heure).

Exemple implicite appris : « SITE003 vers 14h » peut avoir un profil très
différent de « SITE001 vers 08h », sans feature croisée explicite.

### Volume de données limité au démarrage

Au lancement du projet, l'historique disponible reste modeste (centaines de
lignes, en croissance avec l'ETL). À cette échelle :

| Approche | Limite pour notre cas |
|---|---|
| Régression linéaire | Trop simple — relation linéaire site/heure → kWh peu réaliste |
| Réseau de neurones | Risque de sur-apprentissage, déploiement plus lourd |
| SVR | Lent, sensible au scaling, tuning plus délicat |
| **Random Forest** | Robuste, peu de réglages, adapté aux petits jeux tabulaires |

### Robustesse opérationnelle

- Pas de **normalisation** obligatoire des features numériques.
- **Tolérant aux outliers** (lectures atypiques).
- `OneHotEncoder(handle_unknown="ignore")` : un site inconnu en inférence ne
  fait pas planter le modèle.
- Entraînement **rapide** — compatible avec un ré-entraînement quotidien (cron
  prévu en phase 2).
- **100 % scikit-learn** : sérialisation `joblib`, intégration native dans le
  `Pipeline` existant.

### Baseline pour valider la chaîne complète

En phase 1, l'objectif prioritaire est de boucler :

```
Postgres → features → entraînement → MinIO → (futur) /predict
```

Le Random Forest est un **baseline solide et interchangeable** : il permet
de livrer l'infrastructure ML sans bloquer des semaines sur le tuning
algorithmique. Le modèle vit dans `create_model_pipeline()` — le remplacer
ne impacte ni les ports ni le stockage MinIO.

## Paramètres actuels

```python
RandomForestRegressor(n_estimators=100, random_state=42)
```

| Paramètre | Valeur | Raison |
|---|---|---|
| `n_estimators` | 100 | Compromis qualité / temps d'entraînement sur notre volume |
| `random_state` | 42 | Reproductibilité des runs et des métriques (MAE, RMSE) |

## Ce qui a été validé empiriquement

Les tests internes ont porté sur les **features**, pas sur le comparatif
d'algorithmes :

| Configuration | Résultat |
|---|---|
| `site_id + hour + minute + temperature_celsius` | MAE / RMSE **plus élevés** |
| `site_id + hour + minute` (sans température) | **Meilleur** sur nos données |

Conclusion : le gain prioritaire vient du **feature engineering** et du
volume de données, pas encore du choix RF vs autre algorithme.

## Alternatives pour la phase 2

| Modèle | Intérêt | Quand l'envisager |
|---|---|---|
| **HistGradientBoostingRegressor** / XGBoost / LightGBM | Souvent meilleur sur données tabulaires | Plus d'historique + features enrichies (lags, jour de semaine) |
| **Ridge / ElasticNet** | Baseline linéaire interprétable | Benchmark pour quantifier le gain du non-linéaire |
| **Prophet / ARIMA** | Série temporelle par site | Si la cible devient « conso des N prochaines heures pour un site » |
| **Modèle par site** | Un estimateur léger par `site_id` | Profils de sites très hétérogènes |

Un benchmark formel **RF vs Gradient Boosting** est prévu une fois les
features lag (`consumption_kwh` t-1h, t-24h) et un historique plus long
en place.

## Synthèse

| Critère | Random Forest |
|---|---|
| Type de problème | Régression tabulaire |
| Taille des données | Adapté au démarrage (~500+ lignes) |
| Features mixtes | Catégoriel + numérique sans scaling |
| Complexité ops | Faible (sklearn natif, joblib) |
| Objectif phase 1 | Baseline fiable pour l'infra, pas le modèle final optimal |

Le `RandomForestRegressor` n'est pas le meilleur modèle possible en absolu —
c'est le **bon compromis** pour avancer sur l'architecture tout en obtenant
des prédictions exploitables dès la première itération.
