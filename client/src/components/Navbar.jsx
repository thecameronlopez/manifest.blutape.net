import { useLocation, useNavigate } from "react-router-dom";
import styles from "./Navbar.module.css";

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 16V4" />
    <path d="m7.5 8.5 4.5-4.5 4.5 4.5" />
    <path d="M4 20h16" />
  </svg>
);

const CreateIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

const SearchIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
);

const items = [
  { path: "/", label: "Upload", Icon: UploadIcon },
  { path: "/create-manifest", label: "Create", Icon: CreateIcon },
  { path: "/search", label: "Search", Icon: SearchIcon },
];

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className={styles.navbar} aria-label="Primary">
      {items.map(({ path, label, Icon }) => {
        const isActive =
          path === "/"
            ? location.pathname === "/" || location.pathname === "/new-manifest"
            : location.pathname === path;
        return (
          <button
            key={path}
            type="button"
            onClick={() => navigate(path)}
            className={`${styles.navButton} ${isActive ? styles.active : ""}`}
            aria-current={isActive ? "page" : undefined}
          >
            <span className={styles.icon}>
              <Icon />
            </span>
            <span className={styles.label}>{label}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default Navbar;
