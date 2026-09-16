"""Comble consumption_kwh par forward-fill au fil de l'eau, lecture par
lecture, sans repasser par MinIO ni Postgres pour retrouver l'historique.

Stateful par nature (contrairement à une fonction pure) : l'imputeur
mémorise en mémoire la dernière valeur connue de chaque site au fil des
cycles du worker.
"""

METHOD_FORWARD_FILL = "forward_fill"
METHOD_NO_HISTORY = "no_history"


class ConsumptionKwhImputer:
    """Mémorise la dernière valeur connue de consumption_kwh, par site."""

    def __init__(self):
        self._last_known: dict[str, float] = {}

    def impute(self, site_id: str, value: float | None) -> tuple[float | None, str | None]:
        """Retourne (valeur_retenue, méthode) pour ce site.

        `méthode` vaut :
        - None si `value` était déjà connue (rien à combler) ;
        - METHOD_FORWARD_FILL si `value` était manquante et qu'une valeur
          antérieure connue a pu être reprise à sa place ;
        - METHOD_NO_HISTORY si `value` était manquante et qu'aucune
          valeur antérieure n'est disponible pour ce site (premier cycle
          après un redémarrage du worker, ou site jamais vu) — la valeur
          reste None, distinct d'un trou normal comblé.
        """
        if value is not None:
            self._last_known[site_id] = value
            return value, None
        last_value = self._last_known.get(site_id)
        if last_value is not None:
            return last_value, METHOD_FORWARD_FILL
        return None, METHOD_NO_HISTORY
