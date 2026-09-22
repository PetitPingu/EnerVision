/**
 * Tranches d'horizon = target_timestamp - "maintenant", en miroir de
 * apps/etl_worker/domain/model_health.py:HORIZON_BUCKETS. Sert à choisir la
 * bonne valeur de mae_by_horizon pour élargir la marge d'erreur autour de
 * la courbe de prévision avec l'horizon (docs/monitoring_model.md).
 */
const HORIZON_BUCKETS: { label: string; minSeconds: number; maxSeconds: number }[] = [
  { label: "0-1h", minSeconds: 0, maxSeconds: 3600 },
  { label: "1-3h", minSeconds: 3600, maxSeconds: 3 * 3600 },
  { label: "3-6h", minSeconds: 3 * 3600, maxSeconds: 6 * 3600 },
  { label: "6-12h", minSeconds: 6 * 3600, maxSeconds: 12 * 3600 },
  { label: "12-24h", minSeconds: 12 * 3600, maxSeconds: 24 * 3600 },
  { label: "1-3j", minSeconds: 24 * 3600, maxSeconds: 3 * 24 * 3600 },
  { label: "3-7j", minSeconds: 3 * 24 * 3600, maxSeconds: 7 * 24 * 3600 },
];

/** Tranche correspondant à `horizonSeconds`, ou null si hors bornes. */
export function horizonBucketLabel(horizonSeconds: number): string | null {
  if (horizonSeconds < 0) {
    return null;
  }
  const bucket = HORIZON_BUCKETS.find(
    (b) => horizonSeconds >= b.minSeconds && horizonSeconds < b.maxSeconds,
  );
  return bucket?.label ?? null;
}

/**
 * MAE à utiliser pour un point à `targetIso`, vu depuis `nowIso` :
 * la valeur de la tranche d'horizon correspondante si disponible, sinon
 * `fallbackMae` (MAE 24h globale) — jamais null si fallbackMae ne l'est pas,
 * pour qu'un trou dans le profil par horizon n'efface pas la bande.
 */
export function maeForHorizon(
  targetIso: string,
  nowIso: string,
  maeByHorizon: Record<string, number>,
  fallbackMae: number | null,
): number | null {
  const horizonSeconds = (new Date(targetIso).getTime() - new Date(nowIso).getTime()) / 1000;
  const bucket = horizonBucketLabel(horizonSeconds);
  if (bucket && maeByHorizon[bucket] !== undefined) {
    return maeByHorizon[bucket];
  }
  return fallbackMae;
}
