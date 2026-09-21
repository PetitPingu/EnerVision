"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { login as loginRequest } from "@/lib/api/auth";
import { setAuthToken, setUnauthorizedHandler } from "@/lib/api/client";
import { decodeJwtPayload } from "@/lib/jwt";

const TOKEN_STORAGE_KEY = "enervision.auth.token";

type AuthContextValue = {
  isAuthenticated: boolean;
  isLoading: boolean;
  email: string | null;
  role: string | null;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    function restoreStoredToken() {
      let stored: string | null = null;
      try {
        stored = localStorage.getItem(TOKEN_STORAGE_KEY);
      } catch {
        stored = null;
      }

      if (stored) {
        setToken(stored);
        setAuthToken(stored);
      }
      setIsLoading(false);
    }

    restoreStoredToken();
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setAuthToken(null);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // stockage indisponible (ex. navigation privée) : rien à nettoyer
    }
    // Sans ça, se déconnecter depuis /admin laisse l'utilisateur sur une
    // page qui n'a plus le droit de s'afficher (voir AdminUsersScreen).
    router.push("/");
  }, [router]);

  // Réagit à un 401 renvoyé par n'importe quel appel apiClient (token
  // expiré/invalide) en repassant l'UI en état déconnecté.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const accessToken = await loginRequest(email, password);
    setToken(accessToken);
    setAuthToken(accessToken);
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    } catch {
      // stockage indisponible : la session ne survivra pas à un rechargement
    }
  }, []);

  const claims = useMemo(() => (token ? decodeJwtPayload(token) : null), [token]);
  const email = claims?.sub ?? null;
  const role = claims?.role ?? null;

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: !!token,
      isLoading,
      email,
      role,
      isAdmin: role === "admin",
      login,
      logout,
    }),
    [token, isLoading, email, role, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé dans un AuthProvider");
  }
  return context;
}
