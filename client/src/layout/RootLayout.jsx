import React, { useEffect, useMemo } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Navbar from "../components/Navbar";
import { useAuth } from "../auth-context";

const RootLayout = () => {
  const navigate = useNavigate();
  const { user, loading, error } = useAuth();
  const fallbackBltapeUrl = "https://blutape.net";

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const returnTo = params.get("return_to");
    if (returnTo) {
      sessionStorage.setItem("blutape_return_to", returnTo);
    }
  }, []);

  const blutapeUrl = useMemo(() => {
    return sessionStorage.getItem("blutape_return_to") || fallbackBltapeUrl;
  }, []);

  if (loading) {
    return (
      <>
        <header>
          <div className="header-brand" onClick={() => navigate("/")}>
            <img
              src="/blu-logo-512.png"
              alt="bluTape logo"
              className="header-logo"
            />
            <div className="header-brand-copy">
              <strong>Manifest</strong>
            </div>
          </div>
        </header>
        <main>
          <p>Checking manifest access...</p>
        </main>
        <Toaster position="top-center" reverseOrder={true} />
      </>
    );
  }

  if (!user) {
    return (
      <>
        <header>
          <div className="header-brand" onClick={() => navigate("/")}>
            <img
              src="/blu-logo-512.png"
              alt="bluTape logo"
              className="header-logo"
            />
            <div className="header-brand-copy">
              <strong>Manifest</strong>
            </div>
          </div>
          <button
            type="button"
            className="header-launch"
            onClick={() => {
              window.location.href = blutapeUrl;
            }}
          >
            blutape
          </button>
        </header>
        <main>
          <p>{error || "You do not have access to this manifest session."}</p>
        </main>
        <Toaster position="top-center" reverseOrder={true} />
      </>
    );
  }

  return (
    <>
      <header>
        <div className="header-brand" onClick={() => navigate("/")}>
          <img
            src="/blu-logo-512.png"
            alt="bluTape logo"
            className="header-logo"
          />
          <div className="header-brand-copy">
            <strong>Manifest</strong>
          </div>
        </div>
        <button
          type="button"
          className="header-launch"
          onClick={() => {
            window.location.href = blutapeUrl;
          }}
        >
          blutape
        </button>
      </header>
      <main>
        <Outlet />
      </main>
      <Navbar />
      <footer>
        <p>Matt's Appliances, LLC</p>
      </footer>
      <Toaster position="top-center" reverseOrder={true} />
    </>
  );
};

export default RootLayout;
