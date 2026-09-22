"use client";

import { useEffect, useRef, useState } from "react";
import { getSensorsStatus } from "@/lib/api/sensors";
import type { SensorsStatusResponse, SiteSensorStatus } from "@/types/sensorStatus";

/**
 * Chaque poll renvoie un JSON tout neuf : même quand la valeur d'un site
 * n'a pas changé, sa référence d'objet, elle, change à chaque fois. Sans ce
 * merge, React.memo sur SiteCard ne servirait à rien (nouvelle référence de
 * prop à chaque poll = re-render systématique de toutes les cartes). En
 * réutilisant la référence précédente pour les sites identiques, seuls les
 * sites qui ont réellement changé provoquent un re-render.
 */
function mergePreservingUnchanged(
  previous: SensorsStatusResponse,
  next: SensorsStatusResponse,
): SensorsStatusResponse {
  const merged: SensorsStatusResponse = {};
  for (const [siteId, nextStatus] of Object.entries(next)) {
    const previousStatus = previous[siteId];
    merged[siteId] =
      previousStatus && isSameStatus(previousStatus, nextStatus)
        ? previousStatus
        : nextStatus;
  }
  return merged;
}

function isSameStatus(a: SiteSensorStatus, b: SiteSensorStatus): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// L'API mock est un instantané, sans flux temps réel (contrairement à
// /api/v1/alerts/stream) : on la repolle nous-mêmes. 15s donne une mise à
// jour quasi temps réel sans marteler l'API mock partagée entre étudiants
// (voir la note sur le rate limiting côté sensors/status).
const POLL_INTERVAL_MS = 15_000;

type UseSensorsStatusResult = {
  data: SensorsStatusResponse;
  isLoading: boolean;
  error: Error | null;
  lastUpdatedAt: Date | null;
};

export function useSensorsStatus(): UseSensorsStatusResult {
  const [data, setData] = useState<SensorsStatusResponse>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const hasLoadedOnce = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchSensorsStatus() {
      if (!hasLoadedOnce.current) {
        setIsLoading(true);
      }

      try {
        const status = await getSensorsStatus();
        if (!cancelled) {
          setData((previous) => mergePreservingUnchanged(previous, status));
          setError(null);
          setLastUpdatedAt(new Date());
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Erreur de chargement"),
          );
          // Un poll qui échoue ne doit pas vider un affichage déjà à jour —
          // seul l'échec du tout premier chargement retombe sur {}.
          if (!hasLoadedOnce.current) {
            setData({});
          }
        }
      } finally {
        if (!cancelled) {
          hasLoadedOnce.current = true;
          setIsLoading(false);
        }
      }
    }

    fetchSensorsStatus();
    const intervalId = setInterval(fetchSensorsStatus, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  return { data, isLoading, error, lastUpdatedAt };
}
