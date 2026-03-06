import styles from "./NewManifest.module.css";
import React, { useState } from "react";
import toast from "react-hot-toast";

const NewManifest = () => {
  const [formData, setFormData] = useState({
    truck_id: "",
    manifest_id: "",
    manufacturer: "",
    manifest: null,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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

  return (
    <div className={styles.newManifestPage}>
      <form
        className={styles.newManifestForm}
        encType="multipart/form-data"
        onSubmit={handleSubmit}
      >
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

        {error && <p role="alert">{error}</p>}
        {success && <p>{success}</p>}
      </form>
    </div>
  );
};

export default NewManifest;
