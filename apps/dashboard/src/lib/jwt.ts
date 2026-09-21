/**
 * Décode le payload d'un JWT pour affichage uniquement (ex: email dans le
 * menu utilisateur) — aucune vérification de signature, jamais utilisé
 * pour une décision d'autorisation (le backend est seul juge de la
 * validité du token).
 */
export function decodeJwtPayload(
  token: string,
): { sub?: string; exp?: number; role?: string } | null {
  const payload = token.split(".")[1];
  if (!payload) return null;

  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}
