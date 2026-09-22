"use client";

import { useEffect, useState } from "react";
import { ALERTS_STREAM_ENDPOINT } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveAlerts } from "@/lib/api/alerts";
import type { AlertEvent } from "@/types/alert";

const STORAGE_KEY = "enervision.activeAlerts";
const TOAST_DURATION_MS = 5000;

export type StoredAlert = AlertEvent & {
  read: boolean;
  resolved: boolean;
  resolvedAt: string | null;
};

export type AlertToast = {
  id: string;
  siteId: string;
  timestamp: string;
};

type UseAlertStreamResult = {
  activeAlerts: StoredAlert[];
  hasUnreadAlerts: boolean;
  markAllAsRead: () => void;
  toasts: AlertToast[];
  dismissToast: (id: string) => void;
};

function loadStored(): Record<string, StoredAlert> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveStored(bySite: Record<string, StoredAlert>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bySite));
  } catch {
    // Stockage indisponible (navigation privée, quota) : l'alerte reste
    // affichée pour la session en cours, juste pas persistée au refresh.
  }
}

// Un site n'a jamais qu'une entrée à la fois (par site_id) : au plus une par
// site suivi (~7 dans ce projet), pas un journal illimité — pas besoin de
// plafonner la taille.
//
// Alertes par site, persistées en localStorage pour survivre à un refresh :
// un "alert"/"minor_alert" (re)met le site en cours (non lue, non résolue) —
// une nouvelle alerte sur un site déjà résolu efface son statut "résolu",
// c'est un nouvel incident. Un "recovery" NE SUPPRIME PLUS l'entrée : il la
// marque résolue en gardant la data_quality/raisons d'origine (l'historique
// de ce qui s'est passé), avec un toast éphémère en plus pour le signaler
// tout de suite — l'entrée "Résolu" dans la liste sert l'historique, le
// toast sert l'instantané, les deux se complètent. Un "recovery" orphelin
// (site jamais vu dans cette session) est ignoré : rien à résoudre.
//
// Le flux ne pousse que des *transitions* (anti-flood côté etl_worker) : un
// site déjà partial/degraded/critical avant l'ouverture de la page n'y
// apparaîtrait jamais tant qu'il ne change pas de zone. Au montage, un appel
// à /api/v1/alerts/active complète donc la liste avec l'état courant, avant
// que le flux ne prenne le relais pour la suite.
export function useAlertStream(): UseAlertStreamResult {
  // Vide côté serveur (SSR) pour ne pas désynchroniser le HTML rendu du
  // premier rendu client : le contenu réel de localStorage n'arrive qu'après
  // le montage, dans l'effet ci-dessous.
  const { isAuthenticated } = useAuth();
  const [activeBySite, setActiveBySite] = useState<Record<string, StoredAlert>>({});
  const [toasts, setToasts] = useState<AlertToast[]>([]);

  function dismissToast(id: string) {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }

  useEffect(() => {
    // /api/v1/alerts/stream n'exige pas de JWT (EventSource ne permet pas
    // d'attacher un header Authorization) et n'est pas filtré par site : on
    // n'ouvre donc la connexion qu'une fois authentifié pour ne rien exposer
    // avant login. Idem pour le localStorage, qui peut contenir l'état d'une
    // session précédente : on l'efface tant que non connecté, et à la
    // déconnexion (passage à false, cleanup ci-dessous ferme l'EventSource).
    if (!isAuthenticated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveBySite({});
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToasts([]);
      return;
    }

    // Lecture ponctuelle d'un système externe (localStorage) au montage,
    // volontairement après le rendu SSR pour éviter un mismatch d'hydratation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveBySite(loadStored());

    const url = `${process.env.NEXT_PUBLIC_API_BFF_URL}${ALERTS_STREAM_ENDPOINT}`;
    const source = new EventSource(url);

    // N'ajoute que les sites du snapshot absents de l'état courant : ne
    // jamais écraser une entrée déjà connue (localStorage, ou déjà mise à
    // jour entre-temps par un événement live reçu pendant que ce fetch
    // était en cours) — évite toute course avec le flux temps réel.
    getActiveAlerts()
      .then((snapshot) => {
        setActiveBySite((prev) => {
          const next = { ...prev };
          let changed = false;
          for (const alert of snapshot) {
            if (!next[alert.site_id]) {
              next[alert.site_id] = { ...alert, read: false, resolved: false, resolvedAt: null };
              changed = true;
            }
          }
          if (changed) saveStored(next);
          return changed ? next : prev;
        });
      })
      .catch(() => {
        // Snapshot indisponible (core_api ou Postgres down) : le flux SSE
        // prendra quand même le relais pour les prochaines transitions.
      });

    function handleAlert(event: MessageEvent<string>) {
      const alertEvent: AlertEvent = JSON.parse(event.data);
      setActiveBySite((prev) => {
        const next = {
          ...prev,
          [alertEvent.site_id]: { ...alertEvent, read: false, resolved: false, resolvedAt: null },
        };
        saveStored(next);
        return next;
      });
    }

    function handleRecovery(event: MessageEvent<string>) {
      const alertEvent: AlertEvent = JSON.parse(event.data);
      // Capturé hors de l'updater (qui doit rester pur — React StrictMode
      // l'invoque deux fois en dev, ce qui déclencherait deux toasts et deux
      // setTimeout si l'effet de bord vivait à l'intérieur).
      let resolvedExisting = false;

      setActiveBySite((prev) => {
        const existing = prev[alertEvent.site_id];
        if (!existing) return prev; // rien à résoudre (recovery orphelin) : pas de toast non plus
        resolvedExisting = true;

        const next = {
          ...prev,
          [alertEvent.site_id]: { ...existing, read: false, resolved: true, resolvedAt: alertEvent.timestamp },
        };
        saveStored(next);
        return next;
      });

      if (resolvedExisting) {
        const toastId = `${alertEvent.site_id}-${alertEvent.timestamp}`;
        setToasts((prev) => [
          ...prev,
          { id: toastId, siteId: alertEvent.site_id, timestamp: alertEvent.timestamp },
        ]);
        setTimeout(() => dismissToast(toastId), TOAST_DURATION_MS);
      }
    }

    source.addEventListener("alert", handleAlert);
    source.addEventListener("minor_alert", handleAlert);
    source.addEventListener("recovery", handleRecovery);

    return () => {
      source.close();
    };
  }, [isAuthenticated]);

  function markAllAsRead() {
    setActiveBySite((prev) => {
      const next = Object.fromEntries(
        Object.entries(prev).map(([siteId, alert]) => [siteId, { ...alert, read: true }]),
      );
      saveStored(next);
      return next;
    });
  }

  const activeAlerts = Object.values(activeBySite).sort((a, b) => {
    if (a.resolved !== b.resolved) return a.resolved ? 1 : -1;
    return b.timestamp.localeCompare(a.timestamp);
  });

  return {
    activeAlerts,
    hasUnreadAlerts: activeAlerts.some((alert) => !alert.read),
    markAllAsRead,
    toasts,
    dismissToast,
  };
}
