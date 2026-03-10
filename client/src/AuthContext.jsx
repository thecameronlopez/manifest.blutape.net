import React, { createContext, useContext, useEffect, useState } from "react";

const AuthContext = createContext(null);

const ACCESS_TOKEN_PARAM = "access_token";

const removeAccessTokenFromUrl = () => {
  const url = new URL(window.location.href);
  if (!url.searchParams.has(ACCESS_TOKEN_PARAM)) return;
  url.searchParams.delete(ACCESS_TOKEN_PARAM);
  window.history.replaceState({}, "", url.toString());
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const bootstrapAuth = async () => {
      try {
        setLoading(true);
        setError("");

        const params = new URLSearchParams(window.location.search);
        const accessToken = params.get(ACCESS_TOKEN_PARAM);

        let response;
        if (accessToken) {
          response = await fetch("/api/auth/session/exchange", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ token: accessToken }),
          });
        } else {
          response = await fetch("/api/auth/session/hydrate");
        }

        const text = await response.text();
        let data = null;

        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          throw new Error("Unable to verify manifest access");
        }

        if (!response.ok || !data?.success) {
          throw new Error(data?.message || "Unable to verify manifest access");
        }

        if (!active) return;

        setUser(data.user || null);
        removeAccessTokenFromUrl();
      } catch (authError) {
        if (!active) return;
        setUser(null);
        setError(authError.message || "Unable to verify manifest access");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    bootstrapAuth();

    return () => {
      active = false;
    };
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        loading,
        error,
        canManage: (user?.role || "").toLowerCase() === "admin",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
