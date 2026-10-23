import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Spin } from "antd";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";

import { api } from "@/api/client";
import type { Me, Permission } from "@/api/types";

interface AuthValue {
  user: Me | null;
  can: (perm: Permission) => boolean;
  setUser: (user: Me | null) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);
const ME_KEY = ["me"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ME_KEY,
    queryFn: () => api.get<Me>("/auth/me").catch(() => null),
    staleTime: Infinity,
  });

  const setUser = useCallback(
    (user: Me | null) => {
      if (user === null) qc.clear();
      qc.setQueryData(ME_KEY, user);
    },
    [qc],
  );

  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("session-expired", onExpired);
    return () => window.removeEventListener("session-expired", onExpired);
  }, [setUser]);

  const logout = useCallback(async () => {
    await api.post("/auth/logout").catch(() => undefined);
    setUser(null);
  }, [setUser]);

  if (isLoading) {
    return <Spin fullscreen />;
  }

  const user = data ?? null;
  const can = (perm: Permission) => !!user?.permissions.includes(perm);
  return <AuthContext.Provider value={{ user, can, setUser, logout }}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
