import styles from "./Manifest.module.css";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { FORMAT_PRICE, dollarsToCents } from "../../utils/tools";
import { useAuth } from "../../auth-context";

const Manifest = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { canManage } = useAuth();
  const [manifest, setManifest] = useState(null);

  // prices[machineId] = { lowes_cents, listed_cents, lowes_draft?, listed_draft? }
  const [prices, setPrices] = useState({});
  // editing["machineId:lowes" | "machineId:listed"] = true/false
  const [editing, setEditing] = useState({});
  const [saving, setSaving] = useState({});
  const [savingAll, setSavingAll] = useState(false);
  const [statusOptions, setStatusOptions] = useState([]);
  const [statusDraft, setStatusDraft] = useState("");
  const [savingStatus, setSavingStatus] = useState(false);
  const [arrivalDateDraft, setArrivalDateDraft] = useState("");
  const [savingArrivalDate, setSavingArrivalDate] = useState(false);
  const [manifestIdDraft, setManifestIdDraft] = useState("");
  const [truckIdDraft, setTruckIdDraft] = useState("");
  const [savingIdentity, setSavingIdentity] = useState(false);
  const [unlockedRows, setUnlockedRows] = useState({});

  const setCents = (machineId, field, cents) => {
    const normalized =
      cents === null || cents === undefined || cents === ""
        ? null
        : Number(cents);
    setPrices((prev) => ({
      ...prev,
      [machineId]: {
        ...prev[machineId],
        [field]: Number.isFinite(normalized) ? normalized : null,
      },
    }));
  };

  const setDraft = (machineId, draftField, value) => {
    setPrices((prev) => ({
      ...prev,
      [machineId]: {
        ...prev[machineId],
        [draftField]: value,
      },
    }));
  };

  const startEditing = (machineId, which, currentCents = 0) => {
    const editKey = `${machineId}:${which}`;
    setEditing((p) => ({ ...p, [editKey]: true }));

    const draftField = which === "lowes" ? "lowes_draft" : "listed_draft";
    setDraft(machineId, draftField, (currentCents / 100).toFixed(2));
  };

  const stopEditing = (machineId, which) => {
    const editKey = `${machineId}:${which}`;
    const centsField = which === "lowes" ? "lowes_cents" : "listed_cents";
    const draftField = which === "lowes" ? "lowes_draft" : "listed_draft";

    const draft = prices[machineId]?.[draftField] ?? "";
    const cents = dollarsToCents(draft);

    setCents(machineId, centsField, cents);

    // Remove draft after commit
    setPrices((prev) => {
      const copy = { ...prev };
      if (copy[machineId]) {
        const { [draftField]: _omit, ...rest } = copy[machineId];
        copy[machineId] = rest;
      }
      return copy;
    });

    setEditing((p) => ({ ...p, [editKey]: false }));
  };

  const printManifest = () => {
    window.print();
  };

  const getPersistedMachineCents = (machine, key) =>
    machine[key === "lowes_cents" ? "lowes_price" : "listed_price"] ?? null;

  const getEffectiveMachineCents = (machine, key) =>
    prices[machine.id]?.[key] ?? getPersistedMachineCents(machine, key);

  const getMachineModelDisplay = (machine) =>
    machine.model || machine.sku || machine.serial || "-";

  const isRowLocked = (machine, lowesCents, listedCents, rowIsEditing, rowIsDirty) => {
    const hasSubmittedBoth =
      (getPersistedMachineCents(machine, "lowes_cents") ?? 0) > 0 &&
      (getPersistedMachineCents(machine, "listed_cents") ?? 0) > 0;
    return (
      hasSubmittedBoth &&
      !unlockedRows[machine.id] &&
      !rowIsEditing &&
      !rowIsDirty
    );
  };

  const submitMachinePrices = async ({
    manifestId,
    machineId,
    lowesCents,
    listedCents,
  }) => {
    setSaving((prev) => ({ ...prev, [machineId]: true }));
    try {
      const response = await fetch("/api/manifest/machine_prices", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: manifestId,
          machine_id: machineId,
          lowes_price_cents: lowesCents,
          listed_price_cents: listedCents,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to save prices");
      }

      const savedMachine = data.payload.machine;
      setCents(machineId, "lowes_cents", savedMachine.lowes_price ?? null);
      setCents(machineId, "listed_cents", savedMachine.listed_price ?? null);
      setManifest((prev) =>
        prev
          ? {
              ...prev,
              machines: prev.machines.map((machine) =>
                machine.id === machineId
                  ? {
                      ...machine,
                      lowes_price: savedMachine.lowes_price ?? null,
                      listed_price: savedMachine.listed_price ?? null,
                    }
                  : machine,
              ),
            }
          : prev,
      );
      setUnlockedRows((prev) => ({ ...prev, [machineId]: false }));
      toast.success("Prices saved");
    } catch (error) {
      console.error("[PRICE_SAVE_ERROR]:", error);
      toast.error(error.message || "Failed to save prices");
    } finally {
      setSaving((prev) => ({ ...prev, [machineId]: false }));
    }
  };

  const submitAllMachinePrices = async () => {
    if (!manifest?.machines?.length) return;
    setSavingAll(true);
    try {
      const items = manifest.machines.map((machine) => ({
        machine_id: machine.id,
        lowes_price_cents: getEffectiveMachineCents(machine, "lowes_cents"),
        listed_price_cents: getEffectiveMachineCents(machine, "listed_cents"),
      }));

      const response = await fetch("/api/manifest/machine_prices/batch", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: manifest.manifest_id,
          items,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to save all prices");
      }

      for (const machine of data.payload.machines || []) {
        setCents(machine.id, "lowes_cents", machine.lowes_price ?? null);
        setCents(machine.id, "listed_cents", machine.listed_price ?? null);
      }
      setManifest((prev) =>
        prev
          ? {
              ...prev,
              machines: prev.machines.map((machine) => {
                const savedMachine = (data.payload.machines || []).find(
                  (item) => item.id === machine.id,
                );

                if (!savedMachine) return machine;

                return {
                  ...machine,
                  lowes_price: savedMachine.lowes_price ?? null,
                  listed_price: savedMachine.listed_price ?? null,
                };
              }),
            }
          : prev,
      );
      setUnlockedRows({});
      toast.success("All prices saved");
    } catch (error) {
      console.error("[PRICE_SAVE_ALL_ERROR]:", error);
      toast.error(error.message || "Failed to save all prices");
    } finally {
      setSavingAll(false);
    }
  };

  const submitManifestStatus = async () => {
    if (!manifest?.manifest_id || !statusDraft) return;
    setSavingStatus(true);
    try {
      const response = await fetch("/api/manifest/status", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: manifest.manifest_id,
          status: statusDraft,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to update status");
      }

      setManifest((prev) =>
        prev ? { ...prev, status: data.payload.status } : prev,
      );
      toast.success("Manifest status updated");
    } catch (error) {
      console.error("[STATUS_SAVE_ERROR]:", error);
      toast.error(error.message || "Failed to update status");
    } finally {
      setSavingStatus(false);
    }
  };

  const submitArrivalDate = async () => {
    if (!manifest?.manifest_id) return;
    setSavingArrivalDate(true);
    try {
      const response = await fetch("/api/manifest/metadata", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          manifest_id: manifest.manifest_id,
          truck_arrival_date: arrivalDateDraft || null,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to update truck arrival date");
      }

      const updatedDate = data.payload.manifest.truck_arrival_date || null;
      setManifest((prev) =>
        prev ? { ...prev, truck_arrival_date: updatedDate } : prev,
      );
      setArrivalDateDraft(updatedDate || "");
      toast.success("Truck arrival date updated");
    } catch (error) {
      console.error("[ARRIVAL_DATE_SAVE_ERROR]:", error);
      toast.error(error.message || "Failed to update truck arrival date");
    } finally {
      setSavingArrivalDate(false);
    }
  };

  const submitIdentityMetadata = async () => {
    if (!manifest?.manifest_id) return;
    const nextManifestId = manifestIdDraft.trim();
    const nextTruckId = truckIdDraft.trim();
    const manifestChanged = nextManifestId !== (manifest.manifest_id || "");
    const truckChanged = nextTruckId !== (manifest.truck_id || "");

    if (!manifestChanged && !truckChanged) return;

    setSavingIdentity(true);
    try {
      const body = {
        manifest_id: manifest.manifest_id,
      };

      if (manifestChanged) {
        body.manifest_id_new = nextManifestId;
      }

      if (truckChanged) {
        body.truck_id = nextTruckId;
      }

      const response = await fetch("/api/manifest/metadata", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to update manifest/truck");
      }

      const updatedManifest = data.payload.manifest;
      setManifest((prev) =>
        prev
          ? {
              ...prev,
              manifest_id: updatedManifest.manifest_id,
              truck_id: updatedManifest.truck_id,
            }
          : prev,
      );
      setManifestIdDraft(updatedManifest.manifest_id || "");
      setTruckIdDraft(updatedManifest.truck_id || "");

      if (updatedManifest.manifest_id && updatedManifest.manifest_id !== id) {
        navigate(`/manifest/${updatedManifest.manifest_id}`, { replace: true });
      }

      toast.success("Manifest/truck updated");
    } catch (error) {
      console.error("[IDENTITY_SAVE_ERROR]:", error);
      toast.error(error.message || "Failed to update manifest/truck");
    } finally {
      setSavingIdentity(false);
    }
  };

  useEffect(() => {
    const gitem = async () => {
      try {
        const [manifestResponse, statusResponse] = await Promise.all([
          fetch(`/api/manifest/?include_machines=true&many=false&manifest_id=${id}`),
          fetch("/api/manifest/status_options"),
        ]);
        const manifestData = await manifestResponse.json();
        const statusData = await statusResponse.json();

        if (!manifestData.success)
          throw new Error(manifestData.message || "There was an error");
        if (!statusResponse.ok || !statusData.success) {
          throw new Error(statusData.message || "Could not load status options");
        }

        setManifest(manifestData.payload.manifest);
        setStatusDraft(manifestData.payload.manifest.status || "");
        setArrivalDateDraft(
          manifestData.payload.manifest.truck_arrival_date || "",
        );
        setManifestIdDraft(manifestData.payload.manifest.manifest_id || "");
        setTruckIdDraft(manifestData.payload.manifest.truck_id || "");
        setStatusOptions(statusData.payload.status_options || []);
        setUnlockedRows({});
      } catch (error) {
        console.error("[ERROR]: ", error);
        toast.error(error.message);
      }
    };
    gitem();
  }, [id]);

  useEffect(() => {
    if (!manifest) return;
    if (searchParams.get("print") !== "1") return;

    const t = setTimeout(() => {
      window.print();
    }, 250);
    return () => clearTimeout(t);
  }, [manifest, searchParams]);

  if (!manifest) return <h1>Nope</h1>;

  return (
    <div className={styles.manifestPage}>
      <div className={styles.manifestActions}>
        <div className={styles.leftActions}>
          <button type="button" onClick={printManifest}>
            Print Manifest Sheet
          </button>
          {canManage && (
            <button
              type="button"
              onClick={submitAllMachinePrices}
              disabled={savingAll}
            >
              {savingAll ? "Saving All..." : "Save All Prices"}
            </button>
          )}
        </div>
        {canManage && (
          <div className={styles.metaActions}>
            <div className={styles.statusActions}>
              <label htmlFor="manifest_status">Status</label>
              <select
                id="manifest_status"
                value={statusDraft}
                onChange={(e) => setStatusDraft(e.target.value)}
              >
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={submitManifestStatus}
                disabled={savingStatus || !statusDraft}
              >
                {savingStatus ? "Saving Status..." : "Save Status"}
              </button>
            </div>
            <div className={styles.arrivalActions}>
              <label htmlFor="truck_arrival_date">Arrival</label>
              <input
                type="date"
                id="truck_arrival_date"
                value={arrivalDateDraft}
                onChange={(e) => setArrivalDateDraft(e.target.value)}
              />
              <button type="button" onClick={submitArrivalDate} disabled={savingArrivalDate}>
                {savingArrivalDate ? "Saving Date..." : "Save Date"}
              </button>
            </div>
          </div>
        )}
      </div>
      <div className={styles.manifestMetaData}>
        {canManage ? (
          <div className={styles.idEditors}>
            <label htmlFor="manifest_id_edit">Manifest#</label>
            <input
              id="manifest_id_edit"
              type="text"
              value={manifestIdDraft}
              onChange={(e) => setManifestIdDraft(e.target.value)}
            />
            <label htmlFor="truck_id_edit">Truck#</label>
            <input
              id="truck_id_edit"
              type="text"
              value={truckIdDraft}
              onChange={(e) => setTruckIdDraft(e.target.value)}
            />
            <button
              type="button"
              onClick={submitIdentityMetadata}
              disabled={
                savingIdentity ||
                (!manifestIdDraft.trim() && manifestIdDraft !== (manifest.manifest_id || "")) ||
                (!truckIdDraft.trim() && truckIdDraft !== (manifest.truck_id || "")) ||
                (manifestIdDraft.trim() === (manifest.manifest_id || "") &&
                  truckIdDraft.trim() === (manifest.truck_id || ""))
              }
            >
              {savingIdentity ? "Saving..." : "Save IDs"}
            </button>
          </div>
        ) : (
          <div>
            <p>Manifest#: {manifest.manifest_id}</p>
            <p>Truck#: {manifest.truck_id || "Unknown"}</p>
            <p>Manufacturer: {manifest.manufacturer}</p>
          </div>
        )}
        <div>
          <p>Status: {manifest.status}</p>
          <p>Machines: {manifest.machines.length}</p>
          <p>
            Truck Arrival Date:{" "}
            {manifest.truck_arrival_date
              ? manifest.truck_arrival_date
              : "Unknown"}
          </p>
        </div>
      </div>

      {manifest.machines.map((machine) => {
        const machineId = machine.id; // <-- use ONE id everywhere

        const lowesEditKey = `${machineId}:lowes`;
        const listedEditKey = `${machineId}:listed`;

        const lowesIsEditing = !!editing[lowesEditKey];
        const listedIsEditing = !!editing[listedEditKey];
        const rowIsEditing = lowesIsEditing || listedIsEditing;

        const lowesCents = getEffectiveMachineCents(machine, "lowes_cents");
        const listedCents = getEffectiveMachineCents(machine, "listed_cents");
        const rowIsDirty =
          lowesCents !== getPersistedMachineCents(machine, "lowes_cents") ||
          listedCents !== getPersistedMachineCents(machine, "listed_cents");
        const rowLocked = isRowLocked(
          machine,
          lowesCents,
          listedCents,
          rowIsEditing,
          rowIsDirty,
        );

        const lowesDraft = prices[machineId]?.lowes_draft ?? "";
        const listedDraft = prices[machineId]?.listed_draft ?? "";

        return (
          <div key={machineId} className={styles.manifestLineItem}>
            <h3>
              {machine.appliance_type}{" "}
              <span>
                [
                <a
                  href={`https://www.lowes.com/search?searchTerm=${encodeURIComponent(machine.sku)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {machine.sku}
                </a>
                ]
              </span>
            </h3>

            <p className={styles.machineDescription}>{machine.description}</p>

            <p className={styles.machinePrice}>
              <span>MSRP: {FORMAT_PRICE(machine.msrp)}</span>
              <span>Paid: {FORMAT_PRICE(machine.your_cost)}</span>
            </p>

            {canManage && (
              <div className={styles.priceConversions}>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_75)
                  }
                >
                  <span>75%</span>
                  {FORMAT_PRICE(machine.markup_75)}
                </p>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_100)
                  }
                >
                  <span>100%</span>
                  {FORMAT_PRICE(machine.markup_100)}
                </p>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_125)
                  }
                >
                  <span>125%</span>
                  {FORMAT_PRICE(machine.markup_125)}
                </p>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_150)
                  }
                >
                  <span>150%</span>
                  {FORMAT_PRICE(machine.markup_150)}
                </p>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_175)
                  }
                >
                  <span>175%</span>
                  {FORMAT_PRICE(machine.markup_175)}
                </p>
                <p
                  onClick={() =>
                    setCents(machineId, "listed_cents", machine.markup_200)
                  }
                >
                  <span>200%</span>
                  {FORMAT_PRICE(machine.markup_200)}
                </p>
              </div>
            )}

            <form
              className={styles.priceInputs}
              onSubmit={(e) => {
                e.preventDefault();
                submitMachinePrices({
                  manifestId: manifest.manifest_id,
                  machineId,
                  lowesCents,
                  listedCents,
                });
              }}
            >
              <div>
                <label htmlFor={`listed_price_${machineId}`}>
                  Listed Price
                </label>
                <input
                  type="text"
                  id={`listed_price_${machineId}`}
                  value={
                    listedIsEditing
                      ? listedDraft
                      : listedCents
                        ? FORMAT_PRICE(listedCents)
                        : ""
                  }
                  disabled={!canManage || rowLocked}
                  onFocus={() => {
                    if (!canManage) return;
                    startEditing(machineId, "listed", listedCents ?? 0);
                  }}
                  onChange={(e) =>
                    setDraft(machineId, "listed_draft", e.target.value)
                  }
                  onBlur={() => {
                    if (!canManage) return;
                    stopEditing(machineId, "listed");
                  }}
                />
              </div>

              <div>
                <label htmlFor={`lowes_price_${machineId}`}>Lowes Price</label>
                <input
                  type="text"
                  id={`lowes_price_${machineId}`}
                  value={
                    lowesIsEditing
                      ? lowesDraft
                      : lowesCents
                        ? FORMAT_PRICE(lowesCents)
                        : ""
                  }
                  disabled={!canManage || rowLocked}
                  onFocus={() => {
                    if (!canManage) return;
                    startEditing(machineId, "lowes", lowesCents ?? 0);
                  }}
                  onChange={(e) =>
                    setDraft(machineId, "lowes_draft", e.target.value)
                  }
                  onBlur={() => {
                    if (!canManage) return;
                    stopEditing(machineId, "lowes");
                  }}
                />
              </div>

              {canManage &&
                (rowLocked || (!rowIsEditing && !rowIsDirty) ? (
                  <button
                    type="button"
                    onClick={() =>
                      setUnlockedRows((prev) => ({ ...prev, [machineId]: true }))
                    }
                    disabled={!!saving[machineId]}
                  >
                    Edit
                  </button>
                ) : (
                  <button type="submit" disabled={!!saving[machineId]}>
                    {saving[machineId] ? "Saving..." : "Submit"}
                  </button>
                ))}
            </form>
          </div>
        );
      })}

      <section className={styles.printSheet}>
        <h2>Manifest #{manifest.manifest_id}</h2>
        <p>Truck #{manifest.truck_id}</p>
        <p>Manufacturer: {manifest.manufacturer}</p>
        <p>
          Arrival Date: {manifest.truck_arrival_date || "Unknown"} | Machines:{" "}
          {manifest.machines.length}
        </p>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Model</th>
              <th>Description</th>
              <th>MSRP</th>
              <th>Paid</th>
              <th>Listed</th>
              <th>Lowe's</th>
            </tr>
          </thead>
          <tbody>
            {manifest.machines.map((machine, idx) => {
              const lowesCents =
                prices[machine.id]?.lowes_cents ?? machine.lowes_price ?? null;
              const listedCents =
                prices[machine.id]?.listed_cents ?? machine.listed_price ?? null;

              return (
                <tr key={`print-${machine.id}`}>
                  <td>{idx + 1}</td>
                  <td>{machine.appliance_type}</td>
                  <td>{getMachineModelDisplay(machine)}</td>
                  <td>{machine.description}</td>
                  <td>{FORMAT_PRICE(machine.msrp)}</td>
                  <td>{FORMAT_PRICE(machine.your_cost)}</td>
                  <td>{listedCents ? FORMAT_PRICE(listedCents) : "-"}</td>
                  <td>{lowesCents ? FORMAT_PRICE(lowesCents) : "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
};

export default Manifest;
