# Diagramme de séquence du Service Prediction

Implémenté dans `apps/prediction` : `main.py` démarre un `BackgroundScheduler`
(APScheduler) qui appelle `retrain_if_better()` toutes les
`RETRAIN_INTERVAL_HOURS` heures (24 par défaut), en tâche de fond dans le
même process que l'API FastAPI. Le candidat est toujours enregistré dans
MLflow (traçabilité), mais l'alias `current` (celui que `/predict` lit)
n'est réassigné que si son MAE bat celui du champion actuel — voir
`apps/prediction/application/retrain_if_better.py`.

#### Mermaid

```mermaid
sequenceDiagram
    autonumber
    participant Cron as APScheduler interne<br/>(intervalle RETRAIN_INTERVAL_HOURS, 24h par défaut)
    participant Pred as Service Prediction (FastAPI)
    participant PG as PostgreSQL (readings_curated)
    participant MLflow as MLflow (Tracking + Registry)
    participant MinIO as MinIO (S3 - artifact store)

    loop Toutes les RETRAIN_INTERVAL_HOURS heures
        Cron->>Pred: Déclenche retrain_if_better()
        Pred->>PG: SELECT readings_curated (consumption_kwh IS NOT NULL)
        PG-->>Pred: Données d'entraînement
        Pred->>Pred: Entraînement du candidat (pipeline sklearn)
        Pred->>MLflow: get_model_version_by_alias(model_name, "current")
        MLflow-->>Pred: Métadonnées du champion actuel (MAE), ou aucune (1er run)
        Pred->>MLflow: log_params/log_metrics + log_model (nouvelle version, run)
        MLflow->>MinIO: Stocke l'artifact du modèle
        MLflow->>PG: Enregistre run + métriques (backend store MLflow)
        alt Candidat meilleur (ou pas de champion)
            Pred->>MLflow: set_registered_model_alias(model_name, "current", version)
        else Candidat moins bon
            Pred->>Pred: Log "candidat écarté", alias current inchangé
        end
    end

    Note over Pred,MLflow: Pas de modèle gardé en mémoire entre les cycles :<br/>chaque appel à /predict recharge l'alias "current" depuis MLflow<br/>(voir seq_predict_call.md) — la promotion est donc visible immédiatement.
```