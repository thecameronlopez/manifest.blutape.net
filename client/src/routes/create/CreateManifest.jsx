import styles from "./CreateManifest.module.css";
import React, { useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth-context";

const EMPTY_LINE = {
  sku: "",
  appliance_type: "",
  description: "",
  msrp: "",
  your_cost: "",
};

const CreateManifest = () => {
  const navigate = useNavigate();
  const { canManage } = useAuth();
  const [header, setHeader] = useState({
    truck_id: "",
    manifest_id: "",
    manufacturer: "",
    truck_arrival_date: "",
  });
  const [lines, setLines] = useState([{ ...EMPTY_LINE }]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateHeader = (e) => {
    const { name, value } = e.target;
    setHeader((prev) => ({ ...prev, [name]: value }));
  };

  const updateLine = (idx, name, value) => {
    setLines((prev) =>
      prev.map((line, i) => (i === idx ? { ...line, [name]: value } : line)),
    );
  };

  const addLine = () => setLines((prev) => [...prev, { ...EMPTY_LINE }]);

  const removeLine = (idx) => {
    setLines((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((_, i) => i !== idx);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!confirm("Create manifest from these line items?")) return;

    if (!header.truck_id || !header.manifest_id || !header.manufacturer) {
      toast.error("Truck ID, Manifest ID, and Manufacturer are required");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("/api/manifest/manual_manifest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          truck_id: header.truck_id.trim(),
          manifest_id: header.manifest_id.trim(),
          manufacturer: header.manufacturer.trim(),
          truck_arrival_date: header.truck_arrival_date || null,
          lines,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Create failed");
      }

      toast.success(`Manifest ${data.payload.manifest_id} created`);
      navigate(`/manifest/${data.payload.id}`);
    } catch (error) {
      console.error("[CREATE_MANIFEST_ERROR]:", error);
      toast.error(error.message || "Failed to create manifest");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canManage) {
    return (
      <div className={styles.createPage}>
        <form className={styles.createForm}>
          <p>Only admin users can create manifests.</p>
          <button type="button" onClick={() => navigate("/search")}>
            Go To Search
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={styles.createPage}>
      <form className={styles.createForm} onSubmit={handleSubmit}>
        <fieldset className={styles.headerFieldset}>
          <legend>Create New Manifest</legend>
          <div className={styles.headerGrid}>
            <label>
              Truck ID
              <input
                type="text"
                name="truck_id"
                value={header.truck_id}
                onChange={updateHeader}
              />
            </label>
            <label>
              Manifest ID
              <input
                type="text"
                name="manifest_id"
                value={header.manifest_id}
                onChange={updateHeader}
              />
            </label>
            <label>
              Manufacturer
              <input
                type="text"
                name="manufacturer"
                value={header.manufacturer}
                onChange={updateHeader}
              />
            </label>
            <label>
              Truck Arrival Date (Optional)
              <input
                type="date"
                name="truck_arrival_date"
                value={header.truck_arrival_date}
                onChange={updateHeader}
              />
            </label>
          </div>
        </fieldset>

        <div className={styles.linesHeader}>
          <h2>Line Items</h2>
          <button type="button" onClick={addLine}>
            Add Line
          </button>
        </div>

        <div className={styles.linesTable}>
          <div className={styles.linesColumns}>
            <span>SKU</span>
            <span>Appliance Type</span>
            <span>Description</span>
            <span>MSRP</span>
            <span>Your Cost</span>
            <span>Action</span>
          </div>
          {lines.map((line, idx) => (
            <div key={idx} className={styles.lineRow}>
              <label className={styles.fieldCell}>
                <span className={styles.fieldLabel}>SKU</span>
                <input
                  type="text"
                  value={line.sku}
                  onChange={(e) => updateLine(idx, "sku", e.target.value)}
                  placeholder="FLVG7000AW"
                />
              </label>
              <label className={styles.fieldCell}>
                <span className={styles.fieldLabel}>Appliance Type</span>
                <input
                  type="text"
                  value={line.appliance_type}
                  onChange={(e) => updateLine(idx, "appliance_type", e.target.value)}
                  placeholder="Gas Dryer"
                />
              </label>
              <label className={styles.fieldCell}>
                <span className={styles.fieldLabel}>Description</span>
                <input
                  type="text"
                  value={line.description}
                  onChange={(e) => updateLine(idx, "description", e.target.value)}
                  placeholder="7 cu ft vented"
                />
              </label>
              <label className={styles.fieldCell}>
                <span className={styles.fieldLabel}>MSRP</span>
                <input
                  type="text"
                  value={line.msrp}
                  onChange={(e) => updateLine(idx, "msrp", e.target.value)}
                  placeholder="698.00"
                />
              </label>
              <label className={styles.fieldCell}>
                <span className={styles.fieldLabel}>Your Cost</span>
                <input
                  type="text"
                  value={line.your_cost}
                  onChange={(e) => updateLine(idx, "your_cost", e.target.value)}
                  placeholder="450.00"
                />
              </label>
              <div className={styles.fieldCell}>
                <span className={styles.fieldLabel}>Action</span>
                <button
                  type="button"
                  className={styles.removeLineButton}
                  onClick={() => removeLine(idx)}
                  disabled={lines.length <= 1}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating..." : "Create Manifest"}
        </button>
      </form>
    </div>
  );
};

export default CreateManifest;

