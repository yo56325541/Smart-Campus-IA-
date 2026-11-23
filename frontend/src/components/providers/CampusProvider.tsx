"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  CampusApiError,
  createVisitorSession,
  getCurrentUser,
  getVisitorSession,
  linkVisitorSession,
  loginUser,
  registerCandidate,
} from "@/lib/api/campus";
import type {
  LoginIn,
  RegisterIn,
  SessionInfo,
  TokenOut,
  UserOut,
} from "@/lib/types";

const SESSION_STORAGE_KEY = "smartcampus.sessionToken";
const ACCESS_STORAGE_KEY = "smartcampus.accessToken";

interface AuthenticationResult {
  linkedConversations: number;
  sessionConflict: boolean;
  user: UserOut;
}

interface CampusContextValue {
  ready: boolean;
  startupError: string | null;
  sessionToken: string | null;
  sessionInfo: SessionInfo | null;
  accessToken: string | null;
  user: UserOut | null;
  sessionConflict: boolean;
  ensureSession: () => Promise<string>;
  login: (body: LoginIn) => Promise<AuthenticationResult>;
  register: (body: RegisterIn) => Promise<AuthenticationResult>;
  logout: () => void;
}

const CampusContext = createContext<CampusContextValue | null>(null);

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Une erreur inattendue est survenue. Réessayez.";
}

export function CampusProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [startupError, setStartupError] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserOut | null>(null);
  const [sessionConflict, setSessionConflict] = useState(false);

  useEffect(() => {
    let active = true;

    async function initialize() {
      try {
        let token = window.localStorage.getItem(SESSION_STORAGE_KEY);
        let info: SessionInfo | null = null;
        const savedAccessToken =
          window.localStorage.getItem(ACCESS_STORAGE_KEY);

        if (token) {
          try {
            info = await getVisitorSession(token);
          } catch (error) {
            if (!(error instanceof CampusApiError) || error.status !== 401) {
              throw error;
            }
            token = null;
            window.localStorage.removeItem(SESSION_STORAGE_KEY);
          }
        }

        if (token && info?.linked && !savedAccessToken) {
          token = null;
          info = null;
          window.localStorage.removeItem(SESSION_STORAGE_KEY);
        }

        if (!token) {
          const created = await createVisitorSession();
          token = created.session_token;
          window.localStorage.setItem(SESSION_STORAGE_KEY, token);
          info = await getVisitorSession(token);
        }

        if (!active) return;
        setSessionToken(token);
        setSessionInfo(info);

        if (savedAccessToken) {
          try {
            const profile = await getCurrentUser(savedAccessToken);
            setAccessToken(savedAccessToken);
            setUser(profile);
            if (profile.role === "candidat") {
              try {
                await linkVisitorSession(token, savedAccessToken);
              } catch (error) {
                if (!(error instanceof CampusApiError) || error.status !== 409) {
                  throw error;
                }
                setSessionConflict(true);
              }
              info = await getVisitorSession(token);
              if (!active) return;
              setSessionInfo(info);
            }
          } catch (error) {
            if (error instanceof CampusApiError && error.status === 401) {
              window.localStorage.removeItem(ACCESS_STORAGE_KEY);
            } else {
              throw error;
            }
          }
        }
      } catch (error) {
        if (active) setStartupError(getErrorMessage(error));
      } finally {
        if (active) setReady(true);
      }
    }

    void initialize();
    return () => {
      active = false;
    };
  }, []);

  const ensureSession = useCallback(async () => {
    if (!ready) {
      throw new Error("La session visiteur est en cours de préparation.");
    }

    let token = sessionToken;
    let info: SessionInfo | null = null;
    if (token) {
      try {
        info = await getVisitorSession(token);
      } catch (error) {
        if (!(error instanceof CampusApiError) || error.status !== 401) {
          throw error;
        }
        token = null;
      }
    }

    if (!token) {
      const created = await createVisitorSession();
      token = created.session_token;
      window.localStorage.setItem(SESSION_STORAGE_KEY, token);
      info = await getVisitorSession(token);
      setSessionToken(token);
    }

    if (accessToken && user?.role === "candidat") {
      try {
        await linkVisitorSession(token, accessToken);
        setSessionConflict(false);
        info = await getVisitorSession(token);
      } catch (error) {
        if (error instanceof CampusApiError && error.status === 409) {
          setSessionConflict(true);
        } else {
          throw error;
        }
      }
    }

    setSessionInfo(info);
    return token;
  }, [accessToken, ready, sessionToken, user]);

  const finishAuthentication = useCallback(
    async (result: TokenOut, token: string) => {
      window.localStorage.setItem(ACCESS_STORAGE_KEY, result.access_token);
      setAccessToken(result.access_token);
      setUser(result.user);

      const profile = await getCurrentUser(result.access_token);
      setUser(profile);

      let conflict = false;
      let linkedConversations = result.linked_conversations;
      if (profile.role === "candidat") {
        try {
          const linked = await linkVisitorSession(token, result.access_token);
          linkedConversations = Math.max(
            linkedConversations,
            linked.linked_conversations,
          );
        } catch (error) {
          if (error instanceof CampusApiError && error.status === 409) {
            conflict = true;
          } else {
            throw error;
          }
        }

        const info = await getVisitorSession(token);
        setSessionInfo(info);
      }
      setSessionConflict(conflict);

      return {
        linkedConversations,
        sessionConflict: conflict,
        user: profile,
      };
    },
    [],
  );

  const login = useCallback(
    async (body: LoginIn) => {
      const token = await ensureSession();
      const result = await loginUser(body);
      return finishAuthentication(result, token);
    },
    [ensureSession, finishAuthentication],
  );

  const register = useCallback(
    async (body: RegisterIn) => {
      const token = await ensureSession();
      const result = await registerCandidate(body, token);
      return finishAuthentication(result, token);
    },
    [ensureSession, finishAuthentication],
  );

  const logout = useCallback(() => {
    window.localStorage.removeItem(ACCESS_STORAGE_KEY);
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    setAccessToken(null);
    setUser(null);
    setSessionToken(null);
    setSessionInfo(null);
    setSessionConflict(false);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      startupError,
      sessionToken,
      sessionInfo,
      accessToken,
      user,
      sessionConflict,
      ensureSession,
      login,
      register,
      logout,
    }),
    [
      accessToken,
      ensureSession,
      login,
      logout,
      ready,
      register,
      sessionConflict,
      sessionInfo,
      sessionToken,
      startupError,
      user,
    ],
  );

  return (
    <CampusContext.Provider value={value}>{children}</CampusContext.Provider>
  );
}

export function useCampus() {
  const context = useContext(CampusContext);
  if (!context) {
    throw new Error("useCampus doit être utilisé dans CampusProvider.");
  }
  return context;
}
