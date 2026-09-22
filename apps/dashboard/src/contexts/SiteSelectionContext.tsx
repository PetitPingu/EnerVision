"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { DEFAULT_SITE_ID } from "@/config/site";
import { useAuth } from "@/contexts/AuthContext";
import { getSites } from "@/lib/api/sites";
import type { Site } from "@/types/site";

type SiteSelectionContextValue = {
  sites: Site[];
  selectedSiteId: string;
  selectedSite: Site | undefined;
  setSelectedSiteId: (siteId: string) => void;
  isLoading: boolean;
  error: Error | null;
};

const SiteSelectionContext = createContext<SiteSelectionContextValue | null>(
  null,
);

export function SiteSelectionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated } = useAuth();
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState(DEFAULT_SITE_ID);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSites() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getSites();
        if (cancelled) return;

        setSites(data);
        setSelectedSiteId((current) => {
          if (data.some((site) => site.site_id === current)) {
            return current;
          }
          return data[0]?.site_id ?? DEFAULT_SITE_ID;
        });
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Erreur de chargement"),
          );
          setSites([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchSites();

    return () => {
      cancelled = true;
    };
    // Redéclenché sur isAuthenticated : le premier appel a lieu avant que
    // l'utilisateur ne se soit connecté (401), il faut retenter une fois le
    // JWT disponible (voir apiClient, apps/dashboard/src/lib/api/client.ts).
  }, [isAuthenticated]);

  const selectedSite = useMemo(
    () => sites.find((site) => site.site_id === selectedSiteId),
    [sites, selectedSiteId],
  );

  const handleSetSelectedSiteId = useCallback((siteId: string) => {
    setSelectedSiteId(siteId);
  }, []);

  const value = useMemo(
    () => ({
      sites,
      selectedSiteId,
      selectedSite,
      setSelectedSiteId: handleSetSelectedSiteId,
      isLoading,
      error,
    }),
    [
      sites,
      selectedSiteId,
      selectedSite,
      handleSetSelectedSiteId,
      isLoading,
      error,
    ],
  );

  return (
    <SiteSelectionContext.Provider value={value}>
      {children}
    </SiteSelectionContext.Provider>
  );
}

export function useSiteSelection() {
  const context = useContext(SiteSelectionContext);
  if (!context) {
    throw new Error(
      "useSiteSelection doit être utilisé dans un SiteSelectionProvider",
    );
  }
  return context;
}
