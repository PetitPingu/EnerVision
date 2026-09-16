"""Comble consumption_kwh quand il est manquant, lecture par lecture.

L'imputeur garde en mémoire la dernière valeur connue de chaque site,
cycle après cycle — pas besoin de relire MinIO ou Postgres pour
retrouver l'historique.
"""

METHOD_FORWARD_FILL = "forward_fill"
METHOD_NO_HISTORY = "no_history"


class ConsumptionKwhImputer:
    """Mémorise la dernière valeur connue de consumption_kwh, par site."""

    def __init__(self):
        self._last_known: dict[str, float] = {}

    def impute(self, site_id: str, value: float | None) -> tuple[float | None, str | None]:
        """Retourne (valeur_retenue, méthode) pour ce site.

        Trois cas possibles pour `méthode` :
        - `None` — la valeur était déjà connue, rien à faire.
        - `METHOD_FORWARD_FILL` — la valeur manquait, on a repris la
          dernière valeur connue.
        - `METHOD_NO_HISTORY` — la valeur manquait, mais on n'a encore
          rien en mémoire pour ce site (juste après un redémarrage du
          worker, ou site jamais vu) : elle reste `None`.
        """
        if value is not None:
            self._last_known[site_id] = value
            return value, None
        last_value = self._last_known.get(site_id)
        if last_value is not None:
            return last_value, METHOD_FORWARD_FILL
        return None, METHOD_NO_HISTORY
