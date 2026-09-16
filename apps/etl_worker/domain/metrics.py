"""Métrique d'imputation : % de lectures dont consumption_kwh a été
comblé par forward-fill, par site. Fonction pure, calculée sur les
lectures curées par EtlJob (domain.imputation.ConsumptionKwhImputer) —
pas de dépendance à Postgres ni MinIO, pour rester testable en
isolation.
"""

from .imputation import METHOD_FORWARD_FILL


def imputation_metrics(curated_rows: list[dict]) -> dict[str, float]:
    """Retourne {site_id: pourcentage}, relatif au nombre de lectures du
    site dans le lot passé en argument (un cycle du worker).

    Ne compte que les lectures effectivement comblées
    (METHOD_FORWARD_FILL) — pas celles restées None faute d'historique
    (METHOD_NO_HISTORY)."""
    totals: dict[str, int] = {}
    imputed_counts: dict[str, int] = {}

    for row in curated_rows:
        site_id = row["site_id"]
        totals[site_id] = totals.get(site_id, 0) + 1
        if row.get("imputation_methods") == METHOD_FORWARD_FILL:
            imputed_counts[site_id] = imputed_counts.get(site_id, 0) + 1

    return {
        site_id: round(100 * imputed_counts.get(site_id, 0) / total, 2)
        for site_id, total in totals.items()
    }
