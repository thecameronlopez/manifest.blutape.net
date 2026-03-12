import styles from "./Search.module.css";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FORMAT_DATE } from "../../utils/tools";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth-context";

const Search = () => {
  const [manifests, setManifests] = useState(null);
  const [statusOptions, setStatusOptions] = useState([]);
  const [statusDrafts, setStatusDrafts] = useState({});
  const [moreOpen, setMoreOpen] = useState({});
  const [deletingId, setDeletingId] = useState(null);
  const [busyKeys, setBusyKeys] = useState({});
  const navi = useNavigate();
  const { canManage } = useAuth();

  const setBusy = (key, value) => {
    setBusyKeys((prev) => ({ ...prev, [key]: value }));
  };

  const busy = (key) => !!busyKeys[key];
  const isMoreOpen = (id) => !!moreOpen[id];
  const statusChanged = (man) => (statusDrafts[man.id] || man.status) !== man.status;
  const statusValue = (man) => statusDrafts[man.id] || man.status;
  const statusToneClass = (status) => {
    if (status === "completed") return styles.statusCompleted;
    if (status === "priced") return styles.statusPriced;
    return styles.statusPending;
  };

  const todayIso = () => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  };

  const loadManifests = async () => {
    try {
      const [manifestResponse, statusResponse] = await Promise.all([
        fetch("/api/manifest/?include_machines=false&many=true&limit=25"),
        fetch("/api/manifest/status_options"),
      ]);
      const manifestData = await manifestResponse.json();
      const statusData = await statusResponse.json();
      if (!manifestData.success) {
        throw new Error(manifestData.message || "There was an error");
      }
      if (!statusResponse.ok || !statusData.success) {
        throw new Error(statusData.message || "Could not load status options");
      }

      const loadedManifests = manifestData.payload.manifests || [];
      setManifests(loadedManifests);
      setStatusOptions(statusData.payload.status_options || []);
      setStatusDrafts(
        loadedManifests.reduce((acc, man) => {
          acc[man.id] = man.status || "";
          return acc;
        }, {}),
      );
    } catch (error) {
      console.error("[ERROR]: ", error);
      toast.error(error.message);
    }
  };

  useEffect(() => {
    loadManifests();
  }, []);

  const handleDelete = async (e, man) => {
    e.stopPropagation();
    const ok = confirm(
      `Delete manifest ${man.manifest_id}? This will remove all machines tied to it.`,
    );
    if (!ok) return;

    setDeletingId(man.id);
    try {
      const response = await fetch(`/api/manifest/${man.id}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Delete failed");
      }

      setManifests((prev) => (prev || []).filter((m) => m.id !== man.id));
      setStatusDrafts((prev) => {
        const copy = { ...prev };
        delete copy[man.id];
        return copy;
      });
      toast.success(`Deleted manifest ${man.manifest_id}`);
    } catch (error) {
      console.error("[DELETE_MANIFEST_ERROR]:", error);
      toast.error(error.message || "Failed to delete manifest");
    } finally {
      setDeletingId(null);
    }
  };

  const handlePrint = (e, man) => {
    e.stopPropagation();
    window.open(
      `/manifest/${encodeURIComponent(man.manifest_id)}?print=1`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleCopyManifestId = async (e, man) => {
    e.stopPropagation();
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(man.manifest_id);
      } else {
        throw new Error("Clipboard not available");
      }
      toast.success(`Copied ${man.manifest_id}`);
    } catch {
      toast.error("Could not copy manifest id");
    }
  };

  const handleExportCsv = (e, man) => {
    e.stopPropagation();
    window.open(
      `/api/manifest/${man.id}/export.csv`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleMarkArrivedToday = async (e, man) => {
    e.stopPropagation();
    const busyKey = `arrive:${man.id}`;
    setBusy(busyKey, true);
    try {
      const response = await fetch("/api/manifest/metadata", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: man.manifest_id,
          truck_arrival_date: todayIso(),
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Failed to set arrival date");
      }

      const updated = data.payload.manifest;
      setManifests((prev) =>
        (prev || []).map((m) =>
          m.id === man.id
            ? { ...m, truck_arrival_date: updated.truck_arrival_date }
            : m,
        ),
      );
      toast.success(`Arrival set for ${man.manifest_id}`);
    } catch (error) {
      console.error("[ARRIVAL_TODAY_ERROR]:", error);
      toast.error(error.message || "Failed to set arrival date");
    } finally {
      setBusy(busyKey, false);
    }
  };

  const handleSaveStatus = async (e, man) => {
    e.stopPropagation();
    const nextStatus = statusDrafts[man.id] || man.status;
    const busyKey = `status:${man.id}`;
    setBusy(busyKey, true);
    try {
      const response = await fetch("/api/manifest/status", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: man.manifest_id,
          status: nextStatus,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Failed to save status");
      }

      setManifests((prev) =>
        (prev || []).map((m) =>
          m.id === man.id ? { ...m, status: data.payload.status } : m,
        ),
      );
      setStatusDrafts((prev) => ({ ...prev, [man.id]: data.payload.status }));
      toast.success(`Status updated: ${data.payload.status}`);
    } catch (error) {
      console.error("[STATUS_SAVE_ERROR]:", error);
      toast.error(error.message || "Failed to save status");
    } finally {
      setBusy(busyKey, false);
    }
  };

  if (!manifests) {
    return <h1>Nope</h1>;
  }

  return (
    <div className={styles.searchPage}>
      {manifests.map((man, index) => (
        <div key={index} className={styles.manifestTile}>
          <div className={styles.manifestTileTop}>
            <h2>{man.manifest_id}</h2>
            <div
              className={styles.statusControl}
              onClick={(e) => e.stopPropagation()}
            >
              {canManage ? (
                <>
                  <select
                    className={`${styles.statusBadgeSelect} ${statusToneClass(statusValue(man))}`}
                    id={`status_${man.id}`}
                    value={statusValue(man)}
                    onChange={(e) =>
                      setStatusDrafts((prev) => ({ ...prev, [man.id]: e.target.value }))
                    }
                  >
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                  {statusChanged(man) && (
                    <button
                      type="button"
                      className={styles.statusSaveButton}
                      onClick={(e) => handleSaveStatus(e, man)}
                      disabled={busy(`status:${man.id}`)}
                    >
                      {busy(`status:${man.id}`) ? "Saving..." : "Save"}
                    </button>
                  )}
                </>
              ) : (
                <span
                  className={`${styles.statusBadgeSelect} ${statusToneClass(man.status)}`}
                >
                  {man.status}
                </span>
              )}
            </div>
          </div>

          <div className={styles.manifestTileMeta}>
            <p>Maker: {man.manufacturer}</p>
            <p>Created: {FORMAT_DATE(man.created_on)}</p>
            <p>
              Arrival:{" "}
              {man.truck_arrival_date
                ? FORMAT_DATE(man.truck_arrival_date)
                : "Unknown"}
            </p>
            <p>Truck: {man.truck_id || "Unknown"}</p>
          </div>

          <hr className={styles.tileDivider} />

          <div className={styles.primaryActions}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => navi(`/manifest/${encodeURIComponent(man.manifest_id)}`)}
            >
              Open
            </button>
            <button
              type="button"
              className={styles.actionButton}
              onClick={(e) => handlePrint(e, man)}
            >
              Print
            </button>
            <button
              type="button"
              className={`${styles.actionButton} ${styles.moreToggleButton}`}
              onClick={() =>
                setMoreOpen((prev) => ({ ...prev, [man.id]: !prev[man.id] }))
              }
            >
              {isMoreOpen(man.id) ? "Less" : "More"}
            </button>
          </div>

          {isMoreOpen(man.id) && (
            <div className={styles.secondaryActions}>
              <button
                type="button"
                className={styles.actionButton}
                onClick={(e) => handlePrint(e, man)}
              >
                Print
              </button>
              {canManage && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(e) => handleExportCsv(e, man)}
                >
                  Export CSV
                </button>
              )}
              {canManage && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(e) => handleCopyManifestId(e, man)}
                >
                  Copy ID
                </button>
              )}
              {canManage && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(e) => handleMarkArrivedToday(e, man)}
                  disabled={busy(`arrive:${man.id}`)}
                >
                  {busy(`arrive:${man.id}`) ? "Marking..." : "Mark Arrived Today"}
                </button>
              )}
              {canManage && (
                <button
                  type="button"
                  className={styles.deleteButton}
                  onClick={(e) => handleDelete(e, man)}
                  disabled={deletingId === man.id}
                >
                  {deletingId === man.id ? "Deleting..." : "Delete"}
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default Search;
