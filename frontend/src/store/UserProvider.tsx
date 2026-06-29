import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { getCurrentUser, User } from "../api/auth";
import { ApiError } from "../api/client";
import { FinancialProfile, getFinancialProfile } from "../api/profile";
import { clearToken, getToken } from "./tokenService";

type UserContextValue = {
  user: User | null;
  profile: FinancialProfile | null;
  loading: boolean;
  error: string;
  refreshUser: () => Promise<User>;
  refreshProfile: () => Promise<FinancialProfile | null>;
  clearUser: () => void;
};

const UserContext = createContext<UserContextValue | null>(null);

function useProfileState() {
  const [profile, setProfile] = useState<FinancialProfile | null>(null);
  const refreshProfile = useCallback(async () => {
    try {
      const currentProfile = await getFinancialProfile();
      setProfile(currentProfile); return currentProfile;
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) { setProfile(null); return null; }
      throw caught;
    }
  }, []);
  return { profile, setProfile, refreshProfile };
}

function useSessionBootstrap(refreshUser: () => Promise<User>, refreshProfile: () => Promise<FinancialProfile | null>, setLoading: (value: boolean) => void) {
  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    Promise.all([refreshUser(), refreshProfile()])
      .catch(() => undefined).finally(() => setLoading(false));
  }, [refreshProfile, refreshUser]);
}

function useUserState(): UserContextValue {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const { profile, setProfile, refreshProfile } = useProfileState();
  const clearUser = useCallback(() => { clearToken(); setUser(null); setProfile(null); setError(""); }, [setProfile]);
  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser); setError(""); return currentUser;
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) { clearUser(); throw caught; }
      const message = caught instanceof Error ? caught.message : "Unable to load your account.";
      setError(message); throw caught;
    }
  }, [clearUser]);
  useSessionBootstrap(refreshUser, refreshProfile, setLoading);
  return { user, profile, loading, error, refreshUser, refreshProfile, clearUser };
}

export function UserProvider({ children }: { children: ReactNode }) {
  return <UserContext.Provider value={useUserState()}>{children}</UserContext.Provider>;
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) throw new Error("useUser must be used within UserProvider.");
  return context;
}
