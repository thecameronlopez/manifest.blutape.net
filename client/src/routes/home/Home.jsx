import styles from "./Home.module.css";
import React from "react";
import { useNavigate } from "react-router-dom";

const Home = () => {
  const navigate = useNavigate();
  const goTo = (destination) => {
    navigate(destination);
  };
  return (
    <div className={styles.homePage}>
      <div className={styles.homePageButtonBlock}>
        <button onClick={() => goTo("/new-manifest")}>
          Upload New Manifest
        </button>
        <button onClick={() => goTo("/create-manifest")}>
          Create New Manifest
        </button>
        <button onClick={() => goTo("/search")}>Search Manifests</button>
      </div>
    </div>
  );
};

export default Home;
