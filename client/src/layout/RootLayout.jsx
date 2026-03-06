import React from "react";
import { Outlet, useNavigate } from "react-router-dom";
import toast, { Toaster } from "react-hot-toast";
import Navbar from "../components/Navbar";

const RootLayout = () => {
  const navigate = useNavigate();

  return (
    <>
      <header>
        <img
          src="/blu-logo-512.png"
          alt="bluTape logo"
          className="header-logo"
          onClick={() => navigate("/")}
        />
        <button
          type="button"
          className="header-launch"
          onClick={() => toast("blutape routing will be wired soon.")}
        >
          Back to blutape
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
