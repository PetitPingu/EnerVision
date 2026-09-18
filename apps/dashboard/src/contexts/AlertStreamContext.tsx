"use client";

import { createContext, useContext } from "react";
import { useAlertStream } from "@/hooks/alerts/useAlertStream";

type AlertStreamContextValue = ReturnType<typeof useAlertStream>;

const AlertStreamContext = createContext<AlertStreamContextValue | null>(null);

// Un seul EventSource pour toute l'app (la cloche ET les toasts en ont
// besoin) : useAlertStream() n'est appelé qu'ici, pas dans chaque composant
// consommateur, sinon chacun ouvrirait sa propre connexion SSE.
export function AlertStreamProvider({ children }: { children: React.ReactNode }) {
  const value = useAlertStream();

  return <AlertStreamContext.Provider value={value}>{children}</AlertStreamContext.Provider>;
}

export function useAlertStreamContext() {
  const context = useContext(AlertStreamContext);
  if (!context) {
    throw new Error("useAlertStreamContext doit être utilisé dans un AlertStreamProvider");
  }
  return context;
}
