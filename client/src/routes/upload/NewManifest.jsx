import styles from "./NewManifest.module.css";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { FORMAT_DATE } from "../../utils/tools";
import { useAuth } from "../../auth-context";

const NewManifest = () => {
  const navigate = useNavigate();
  const { canManage } = useAuth();
  const [formData, setFormData] = useState({
    truck_id: "",
    manifest_id: "",
    manufacturer: "",
    manifest: null,
  });
  const [buildSourceDate, setBuildSourceDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isBuildingCompleted, setIsBuildingCompleted] = useState(false);
  const [completedCountState, setCompletedCountState] = useState({
    loading: true,
    count: 0,
    sourceDate: "",
    error: "",
  });
  const [countRetryKey, setCountRetryKey] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const loadCompletedCount = async () => {
      setCompletedCountState((prev) => ({
        ...prev,
        loading: true,
        error: "",
      }));

      try {
        const query = buildSourceDate
          ? `?source_date=${encodeURIComponent(buildSourceDate)}`
          : "";
        const response = await fetch(
          `/api/manifest/completed_machines/count${query}`,
          {
            signal: controller.signal,
          },
        );
        const rawText = await response.text();
        let data = null;

        try {
          data = rawText ? JSON.parse(rawText) : null;
        } catch {
          throw new Error(
            "Unable to load completed-machine count right now. The API returned an unexpected response.",
          );
        }

        if (!response.ok || !data.success) {
          throw new Error(data.message || "Failed to load completed machine count");
        }

        if (!active) return;

        setCompletedCountState({
          loading: false,
          count: Number(data.payload?.count || 0),
          sourceDate: data.payload?.source_date || "",
          error: "",
        });
      } catch (countError) {
        if (countError.name === "AbortError" || !active) return;

        setCompletedCountState({
          loading: false,
          count: 0,
          sourceDate: "",
          error: countError.message || "Failed to load completed machine count",
        });
      }
    };

    loadCompletedCount();

    return () => {
      active = false;
      controller.abort();
    };
  }, [buildSourceDate, countRetryKey]);

  const refreshCompletedCount = () => setCountRetryKey((prev) => prev + 1);

  const handleChange = (e) => {
    const { name, value, type, files } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "file" ? (files?.[0] ?? null) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!confirm("Submit manifest?")) return;
    setError("");
    setSuccess("");

    if (!formData.truck_id || !formData.manifest_id || !formData.manufacturer) {
      setError("Truck ID, Manifest ID, and Manufacturer must be set");
      return;
    }

    if (!formData.manifest) {
      setError("Please select a CSV file");
      return;
    }

    const payload = new FormData();
    payload.append("truck_id", formData.truck_id.trim());
    payload.append("manifest_id", formData.manifest_id.trim());
    payload.append("manufacturer", formData.manufacturer.trim());
    payload.append("manifest", formData.manifest);

    try {
      setIsSubmitting(true);

      const response = await fetch("/api/manifest/raw_manifest", {
        method: "POST",
        credentials: "include",
        body: payload,
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || "Upload failed");
      }

      setSuccess(data.message);
      setFormData({
        truck_id: "",
        manifest_id: "",
        manufacturer: "",
        manifest: null,
      });
    } catch (error) {
      console.error("SUBMISSION ERROR: ", error);
      toast.error(error.message || "Upload failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBuildCompletedManifest = async (e) => {
    e.preventDefault();
    const message = buildSourceDate
      ? `Build completed-machine manifest for ${buildSourceDate}?`
      : "Build completed-machine manifest for the previous workday?";
    if (!confirm(message)) return;

    try {
      setIsBuildingCompleted(true);
      const response = await fetch(
        "/api/manifest/completed_machines/build_previous_workday",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_date: buildSourceDate || null,
          }),
        },
      );

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Build failed");
      }

      if (data.payload?.manifest?.id) {
        toast.success(`Manifest ${data.payload.manifest.manifest_id} built`);
        navigate(`/manifest/${data.payload.manifest.id}`);
        return;
      }

      toast.success(data.message || "No completed machines found");
    } catch (buildError) {
      console.error("[BUILD_COMPLETED_MANIFEST_ERROR]:", buildError);
      toast.error(buildError.message || "Failed to build completed-machine manifest");
    } finally {
      setIsBuildingCompleted(false);
    }
  };

  if (!canManage) {
    return (
      <div className={styles.newManifestPage}>
        <div className={styles.newManifestForm}>
          <p role="alert">Only admin users can create or upload manifests.</p>
          <button type="button" onClick={() => navigate("/search")}>
            Go To Search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.newManifestPage}>
      <form
        className={styles.newManifestForm}
        encType="multipart/form-data"
        onSubmit={handleSubmit}
      >
        <section className={styles.completedManifestCard}>
          <div className={styles.completedManifestCopy}>
            <h2>Build From Completed Machines</h2>
            <p>
              Leave the date blank to pull the previous workday. Use a specific
              date only for reruns or backfills.
            </p>
            <p
              className={`${styles.completedManifestCount} ${
                completedCountState.error
                  ? styles.completedManifestCountError
                  : completedCountState.loading
                    ? styles.completedManifestCountLoading
                    : styles.completedManifestCountReady
              }`}
              aria-live="polite"
            >
              {completedCountState.loading && (
                <span className={styles.countStatusBadge}>Checking</span>
              )}
              {completedCountState.loading
                ? "Checking completed machines..."
                : completedCountState.error
                  ? `Unable to load completed-machine count right now. ${completedCountState.error}`
                  : `There ${
                      completedCountState.count === 1 ? "is" : "are"
                    } currently ${completedCountState.count} machine${
                      completedCountState.count === 1 ? "" : "s"
                    } ready for export on ${
                      completedCountState.sourceDate
                        ? FORMAT_DATE(completedCountState.sourceDate)
                        : "the selected date"
                    }.`}
            </p>
            {completedCountState.error && (
              <button
                type="button"
                className={styles.retryCountButton}
                onClick={refreshCompletedCount}
              >
                Retry Count
              </button>
            )}
          </div>
          <div className={styles.completedManifestControls}>
            <label htmlFor="build_source_date">Source Date (Optional)</label>
            <input
              id="build_source_date"
              type="date"
              value={buildSourceDate}
              onChange={(e) => setBuildSourceDate(e.target.value)}
            />
            <button
              type="button"
              className={styles.completedManifestButton}
              onClick={handleBuildCompletedManifest}
              disabled={isBuildingCompleted}
            >
              {isBuildingCompleted ? "Building..." : "Build Completed Manifest"}
            </button>
          </div>
        </section>

        <fieldset>
          <legend>New Manifest</legend>
          <div>
            <input
              type="text"
              name="truck_id"
              id="truck_id"
              value={formData.truck_id}
              onChange={handleChange}
            />
            <label htmlFor="truck_id">Truck ID</label>
          </div>
          <div>
            <input
              type="text"
              name="manifest_id"
              id="manifest_id"
              value={formData.manifest_id}
              onChange={handleChange}
            />
            <label htmlFor="manifest_id">Manifest ID</label>
          </div>
          <div>
            <input
              type="text"
              name="manufacturer"
              id="manufacturer"
              value={formData.manufacturer}
              onChange={handleChange}
            />
            <label htmlFor="manufacturer">Manufacturer</label>
          </div>
          <div>
            <input
              type="file"
              name="manifest"
              id="manifest"
              accept=".csv"
              value={formData.file}
              onChange={handleChange}
            />
            <label htmlFor="manifest" className={styles.customUpload}>
              {formData.manifest ? formData.manifest.name : "CSV File"}
            </label>
          </div>
        </fieldset>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit"}
        </button>

        <div className={styles.templateRow}>
          <a
            className={styles.templateButton}
            href="/api/manifest/template.csv"
            download
          >
            Download CSV Template
          </a>
          <p>
            Template columns: SKU, Appliance Type, Description, MSRP, Your Cost
          </p>
        </div>

        {error && <p role="alert">{error}</p>}
        {success && <p>{success}</p>}
      </form>
    </div>
  );
};

export default NewManifest;
