"""Détecte les transitions de data_quality par site, cycle après cycle.

Comme ConsumptionKwhImputer (domain/imputation.py), l'état est gardé en
mémoire par site — perdu au redémarrage du worker, pas relu depuis MinIO ou
Postgres. Anti-flood : un site qui reste dans la même zone (bonne / mineure /
alerte) sur plusieurs cycles consécutifs ne redéclenche rien, seul le
changement de zone compte.

Trois zones, par sévérité croissante :
- "good"  : good
- "minor" : partial (un souci isolé identifié, mineur mais réel)
- "alert" : degraded / critical

detect_transition() ne modifie plus l'état interne — c'est à l'appelant
d'appeler commit() une fois l'événement effectivement traité (publié avec
succès, ou absent). Sépare la détection de la mémorisation : si la
publication Redis échoue, ne pas commit laisse la même transition détectable
au prochain cycle (retry), plutôt que de la considérer silencieusement
"vue" alors qu'elle n'a jamais été publiée.
"""

EVENT_ALERT = "alert"
EVENT_MINOR_ALERT = "minor_alert"
EVENT_RECOVERY = "recovery"

_ALERT_LEVELS = frozenset({"degraded", "critical"})
_MINOR_LEVEL = "partial"
_GOOD_LEVEL = "good"


def _zone(data_quality: str) -> str:
    if data_quality in _ALERT_LEVELS:
        return "alert"
    if data_quality == _MINOR_LEVEL:
        return "minor"
    return "good"


class DataQualityTransitionDetector:
    """Mémorise la dernière data_quality connue et commitée de chaque site."""

    def __init__(self):
        self._last_state: dict[str, str] = {}

    def detect_transition(self, site_id: str, data_quality: str) -> str | None:
        """Retourne l'événement à publier pour ce site, ou None — sans
        modifier l'état mémorisé (voir commit()).

        - `None` si le site n'a jamais été vu/commité (pas de base de
          comparaison, même logique que METHOD_NO_HISTORY côté imputation),
          ou si la zone ne change pas (ex. degraded <-> critical, partial ->
          partial).
        - `EVENT_ALERT` en entrant dans la zone alerte (good/partial ->
          degraded/critical).
        - `EVENT_MINOR_ALERT` en entrant dans la zone mineure (good ->
          partial, ou degraded/critical -> partial : un souci reste identifié
          même si la situation s'améliore).
        - `EVENT_RECOVERY` en revenant à `good`, depuis n'importe quelle zone.
        """
        previous = self._last_state.get(site_id)
        if previous is None:
            return None

        previous_zone = _zone(previous)
        new_zone = _zone(data_quality)
        if previous_zone == new_zone:
            return None

        if new_zone == "alert":
            return EVENT_ALERT
        if new_zone == "minor":
            return EVENT_MINOR_ALERT
        return EVENT_RECOVERY

    def commit(self, site_id: str, data_quality: str) -> None:
        """Mémorise data_quality comme dernier état connu pour ce site.

        À appeler après avoir traité l'événement retourné par
        detect_transition() — ou immédiatement si detect_transition() a
        retourné None (rien à publier, mais l'état doit quand même avancer).
        Ne pas l'appeler après un échec de publication : la même transition
        sera redétectée au prochain cycle.
        """
        self._last_state[site_id] = data_quality
