from flask import Blueprint, request, jsonify, current_app as MANIFEST_DESTINY
from app.extensions import db
from app.models import Manifest, Machine
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path
from urllib import error, parse, request as urlrequest

from app.utils.file_settings import resolve_upload_path, ensure_directory
from app.utils.helpers import build_header_map
from app.utils.money import parse_dollars_to_cents, cents_to_decimal_str
from app.models.manifest import ManifestKindEnum, ManifestStatusEnum
from app.models.machine import MachineEntryKindEnum



manifest = Blueprint("manifest", __name__)


def allowed_filename(filename: str):
        return "." in filename and \
            filename.rsplit('.',1)[1].lower() in MANIFEST_DESTINY.config["ALLOWED_EXTENSIONS"]
            

def true_or_false(value: str):
    if value.lower() in ["true", "yes", "1"]:
        return True
    elif value.lower() in ["false", "no", "0"]:
        return False


def parse_optional_cents(value, field_name):
    if value is None or value == "":
        return None
    try:
        cents = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer or null")
    if cents < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return cents


def parse_optional_date(value, field_name):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field_name} must be YYYY-MM-DD or null")


def coerce_int(value, field_name, *, required=False):
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_completion_description(item):
    provided = normalize_text(item.get("description"))
    if provided:
        return provided

    parts = [
        normalize_text(item.get("brand")),
        normalize_text(item.get("model")),
        normalize_text(item.get("form_factor")),
        normalize_text(item.get("color")),
    ]
    description = " ".join(part for part in parts if part)
    return description or normalize_text(item.get("serial")) or "Completed machine"


def previous_workday(reference_date: date) -> date:
    weekday = reference_date.weekday()
    if weekday == 0:
        return reference_date - timedelta(days=2)
    if weekday == 6:
        return reference_date - timedelta(days=1)
    return reference_date - timedelta(days=1)


def fetch_blutape_completed_manifest_payload(manifest_date: date):
    base_url = (MANIFEST_DESTINY.config.get("BLUTAPE_API_BASE_URL") or "").rstrip("/")
    integration_key = (MANIFEST_DESTINY.config.get("BLUTAPE_INTEGRATION_KEY") or "").strip()
    if not base_url:
        raise RuntimeError("BLUTAPE_API_BASE_URL is not configured")
    if not integration_key:
        raise RuntimeError("BLUTAPE_INTEGRATION_KEY is not configured")

    query_string = parse.urlencode(
        {"date": manifest_date.isoformat(), "only_unexported": "true"}
    )
    req = urlrequest.Request(
        f"{base_url}/api/export/completed_manifest?{query_string}",
        headers={"X-Integration-Key": integration_key},
        method="GET",
    )

    try:
        with urlrequest.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Blutape export request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Blutape export request failed: {exc.reason}") from exc

    if not payload.get("success"):
        raise RuntimeError(payload.get("message") or "Blutape export request failed")

    return payload.get("payload") or {}


def acknowledge_blutape_manifest_export(manifest_date: date, manifest_id: str, items: list[dict]):
    base_url = (MANIFEST_DESTINY.config.get("BLUTAPE_API_BASE_URL") or "").rstrip("/")
    integration_key = (MANIFEST_DESTINY.config.get("BLUTAPE_INTEGRATION_KEY") or "").strip()
    if not base_url:
        raise RuntimeError("BLUTAPE_API_BASE_URL is not configured")
    if not integration_key:
        raise RuntimeError("BLUTAPE_INTEGRATION_KEY is not configured")

    body = json.dumps(
        {
            "manifest_date": manifest_date.isoformat(),
            "manifest_id": manifest_id,
            "items": items,
        }
    ).encode("utf-8")
    req = urlrequest.Request(
        f"{base_url}/api/export/completed_manifest/ack",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Integration-Key": integration_key,
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Blutape export acknowledge failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Blutape export acknowledge failed: {exc.reason}") from exc

    if not payload.get("success"):
        raise RuntimeError(payload.get("message") or "Blutape export acknowledge failed")

    return payload.get("payload") or {}


def apply_pricing_status(manifest_row: Manifest) -> None:
    # Keep completed manifests stable unless explicitly changed by status endpoint.
    if manifest_row.status == ManifestStatusEnum.COMPLETED:
        return

    has_unlisted = any(m.listed_price is None for m in manifest_row.machines)
    manifest_row.status = (
        ManifestStatusEnum.PENDING if has_unlisted else ManifestStatusEnum.PRICED
    )
    
    

@manifest.post("/raw_manifest")
def upload_raw_manifest():
    file = request.files.get("manifest")
    if not file or not file.filename:
        return jsonify(success=False, message="manifest file required"), 400
    if not allowed_filename(file.filename):
        return jsonify(success=False, message="only csv uploads are allowed"), 400
    
    truck_id = (request.form.get("truck_id") or "").strip()
    manifest_id = (request.form.get("manifest_id") or "").strip()
    manufacturer = (request.form.get("manufacturer") or "").strip().lower()
    truck_arrival_date_raw = (request.form.get("truck_arrival_date") or "").strip()
    
    if not truck_id or not manifest_id or not manufacturer:
        return jsonify(success=False, message="Truck ID, Manifest ID, and Manufacturer are required"), 400
    
    truck_arrival_date = None
    if truck_arrival_date_raw:
        try:
            truck_arrival_date = date.fromisoformat(truck_arrival_date_raw)
        except ValueError:
            return jsonify(success=False, message="truck_arrival_date must be YYYY-MM-DD"), 400
        
    resolved = resolve_upload_path(
        upload_root=MANIFEST_DESTINY.config["UPLOAD_ROOT"],
        manifest_type="new",
        manifest_date=truck_arrival_date or date.today(),
        truck_id=truck_id,
        manifest_id=manifest_id,
        manufacturer=manufacturer,
        suffix="raw",
    )
    
    ensure_directory(resolved.absolute_dir)
    file.save(resolved.absolute_file)
    
    try:
        manifest_row = Manifest(
            truck_arrival_date=truck_arrival_date,
            truck_id=truck_id,
            manifest_id=manifest_id,
            manufacturer=manufacturer,
            manifest_kind=ManifestKindEnum.TRUCK_UPLOAD,
        )
        db.session.add(manifest_row)
        db.session.flush()
        
        with open(resolved.absolute_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_map = build_header_map(reader.fieldnames or [])
            
            line_number = 0
            for row in reader:
                sku = (row.get(header_map["sku"]) or "").strip()
                appliance_type = (row.get(header_map["appliance_type"]) or "").strip()
                description = (row.get(header_map["description"]) or "").strip()
                
                if not sku and not appliance_type and not description:
                    continue
                if sku.lower() in {"totals", "profit"}:
                    continue
                
                line_number += 1
                
                msrp = parse_dollars_to_cents(row.get(header_map["msrp"]))
                your_cost = parse_dollars_to_cents(row.get(header_map["your_cost"]))
                listed_price = (
                    parse_dollars_to_cents(row.get(header_map["listed_price"]))
                    if "listed_price" in header_map
                    else None
                )
                lowes_price = (
                    parse_dollars_to_cents(row.get(header_map["lowes_price"]))
                    if "lowes_price" in header_map
                    else None
                )
                
                if msrp is None or your_cost is None:
                    raise ValueError(f"Missing required money fields at data line {line_number}")
                
                machine = Machine(
                    manifest_pk=manifest_row.id,
                    line_number=line_number,
                    sku=sku,
                    appliance_type=appliance_type,
                    description=description,
                    msrp=msrp,
                    your_cost=your_cost,
                    listed_price=listed_price,
                    lowes_price=lowes_price,
                )
                db.session.add(machine)
        apply_pricing_status(manifest_row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, message="Manifest ID already exists"), 409
    except ValueError as err:
        db.session.rollback()
        return jsonify(success=False, message=f"Value Error: {err}"), 400
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f"Upload failed: {e}"), 500
    finally:
        try:
            Path(resolved.absolute_file).unlink(missing_ok=True)
        except Exception:
            pass
    
    return jsonify(
        success=True,
        id=manifest_row.id,
        manifest_id=manifest_row.manifest_id,
        status=manifest_row.status.value,
        line_items=line_number,
        message="Manifest had been uploaded"
    ), 201


@manifest.post("/manual_manifest")
def create_manual_manifest():
    payload = request.get_json(silent=True) or {}

    truck_id = str(payload.get("truck_id", "")).strip()
    manifest_id = str(payload.get("manifest_id", "")).strip()
    manufacturer = str(payload.get("manufacturer", "")).strip().lower()
    truck_arrival_date_raw = str(payload.get("truck_arrival_date", "")).strip()
    lines = payload.get("lines")

    if not truck_id or not manifest_id or not manufacturer:
        return jsonify(success=False, message="Truck ID, Manifest ID, and Manufacturer are required"), 400
    if not isinstance(lines, list) or not lines:
        return jsonify(success=False, message="At least one line item is required"), 400

    truck_arrival_date = None
    if truck_arrival_date_raw:
        try:
            truck_arrival_date = date.fromisoformat(truck_arrival_date_raw)
        except ValueError:
            return jsonify(success=False, message="truck_arrival_date must be YYYY-MM-DD"), 400

    try:
        manifest_row = Manifest(
            truck_arrival_date=truck_arrival_date,
            truck_id=truck_id,
            manifest_id=manifest_id,
            manufacturer=manufacturer,
            manifest_kind=ManifestKindEnum.MANUAL,
        )
        db.session.add(manifest_row)
        db.session.flush()

        line_number = 0
        for idx, line in enumerate(lines):
            if not isinstance(line, dict):
                raise ValueError(f"Line {idx + 1} must be an object")

            sku = str(line.get("sku", "")).strip()
            appliance_type = str(line.get("appliance_type", "")).strip()
            description = str(line.get("description", "")).strip()
            msrp_raw = line.get("msrp")
            your_cost_raw = line.get("your_cost")

            if not sku and not appliance_type and not description and (msrp_raw in (None, "")) and (your_cost_raw in (None, "")):
                continue

            missing = []
            if not sku:
                missing.append("sku")
            if not appliance_type:
                missing.append("appliance_type")
            if not description:
                missing.append("description")
            if msrp_raw in (None, ""):
                missing.append("msrp")
            if your_cost_raw in (None, ""):
                missing.append("your_cost")
            if missing:
                raise ValueError(f"Line {idx + 1} missing fields: {', '.join(missing)}")

            msrp = parse_dollars_to_cents(msrp_raw)
            your_cost = parse_dollars_to_cents(your_cost_raw)
            if msrp is None or your_cost is None:
                raise ValueError(f"Line {idx + 1} has invalid money values")

            line_number += 1
            db.session.add(
                Machine(
                    manifest_pk=manifest_row.id,
                    line_number=line_number,
                    sku=sku,
                    appliance_type=appliance_type,
                    description=description,
                    msrp=msrp,
                    your_cost=your_cost,
                    listed_price=None,
                    lowes_price=None,
                )
            )

        if line_number == 0:
            raise ValueError("At least one non-empty line item is required")

        apply_pricing_status(manifest_row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, message="Manifest ID already exists"), 409
    except ValueError as err:
        db.session.rollback()
        return jsonify(success=False, message=str(err)), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify(success=False, message=f"Create failed: {exc}"), 500

    return (
        jsonify(
            success=True,
            message="Manual manifest created",
            payload={
                "id": manifest_row.id,
                "manifest_id": manifest_row.manifest_id,
                "status": manifest_row.status.value,
                "line_items": line_number,
            },
        ),
        201,
    )


@manifest.get("/template.csv")
def download_manifest_template():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    # Use canonical headers accepted by build_header_map aliases.
    writer.writerow(
        [
            "SKU",
            "Appliance Type",
            "Description",
            "MSRP",
            "Your Cost",
            "Listed Price",
            "Lowes Price",
        ]
    )

    csv_data = buffer.getvalue()
    buffer.close()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="manifest_template.csv"',
        },
    )


def upsert_completed_machines_manifest(payload):
    manifest_date_raw = payload.get("manifest_date")
    machines = payload.get("machines")
    provided_manifest_id = normalize_text(payload.get("manifest_id"))

    if not manifest_date_raw:
        raise ValueError("manifest_date is required")
    if not isinstance(machines, list) or not machines:
        raise ValueError("machines must be a non-empty array")

    manifest_date = parse_optional_date(manifest_date_raw, "manifest_date")
    manifest_id = provided_manifest_id or f"BLU-COMP-{manifest_date.strftime('%Y%m%d')}"
    truck_id = f"blutape-completed-{manifest_date.strftime('%Y%m%d')}"

    manifest_row = (
        db.session.query(Manifest)
        .filter(
            Manifest.manifest_kind == ManifestKindEnum.BLUTAPE_COMPLETED_DAILY,
            Manifest.source_system == "blutape",
            Manifest.source_date == manifest_date,
        )
        .first()
    )

    if manifest_row is None and provided_manifest_id:
        manifest_row = db.session.query(Manifest).filter_by(manifest_id=manifest_id).first()
        if manifest_row and manifest_row.manifest_kind != ManifestKindEnum.BLUTAPE_COMPLETED_DAILY:
            raise ValueError("manifest_id already belongs to a non-Blutape manifest")

    if manifest_row is None:
        manifest_row = Manifest(
            truck_arrival_date=manifest_date,
            truck_id=truck_id,
            manifest_id=manifest_id,
            manufacturer="blutape",
            manifest_kind=ManifestKindEnum.BLUTAPE_COMPLETED_DAILY,
            source_system="blutape",
            source_date=manifest_date,
        )
        db.session.add(manifest_row)
        db.session.flush()
    else:
        manifest_row.truck_arrival_date = manifest_date
        manifest_row.truck_id = truck_id
        manifest_row.manifest_id = manifest_id
        manifest_row.manufacturer = "blutape"
        manifest_row.manifest_kind = ManifestKindEnum.BLUTAPE_COMPLETED_DAILY
        manifest_row.source_system = "blutape"
        manifest_row.source_date = manifest_date

    existing_by_source_machine_id = {
        machine.source_machine_id: machine
        for machine in manifest_row.machines
        if machine.source_machine_id is not None
    }
    used_machine_ids = set()

    line_number = 0
    for idx, item in enumerate(machines):
        if not isinstance(item, dict):
            raise ValueError(f"machines[{idx}] must be an object")

        source_machine_id = coerce_int(
            item.get("blutape_machine_id"),
            f"machines[{idx}].blutape_machine_id",
            required=True,
        )
        source_work_order_id = coerce_int(
            item.get("blutape_work_order_id"),
            f"machines[{idx}].blutape_work_order_id",
        )
        source_event_id = coerce_int(
            item.get("blutape_event_id"),
            f"machines[{idx}].blutape_event_id",
        )
        completed_on = parse_optional_date(
            item.get("completed_on"),
            f"machines[{idx}].completed_on",
        )

        serial = normalize_text(item.get("serial"))
        appliance_type = (
            normalize_text(item.get("category"))
            or normalize_text(item.get("appliance_type"))
            or "unknown"
        )
        description = build_completion_description(item)

        line_number += 1
        machine_row = existing_by_source_machine_id.get(source_machine_id)
        if machine_row is None:
            machine_row = Machine(
                manifest_pk=manifest_row.id,
                line_number=line_number,
                entry_kind=MachineEntryKindEnum.BLUTAPE_COMPLETION,
                source_machine_id=source_machine_id,
                listed_price=None,
                lowes_price=None,
            )
            db.session.add(machine_row)

        machine_row.line_number = line_number
        machine_row.entry_kind = MachineEntryKindEnum.BLUTAPE_COMPLETION
        machine_row.source_machine_id = source_machine_id
        machine_row.source_work_order_id = source_work_order_id
        machine_row.source_event_id = source_event_id
        machine_row.serial = serial
        machine_row.brand = normalize_text(item.get("brand"))
        machine_row.model = normalize_text(item.get("model"))
        machine_row.vendor = normalize_text(item.get("vendor"))
        machine_row.condition = normalize_text(item.get("condition"))
        machine_row.color = normalize_text(item.get("color"))
        machine_row.form_factor = normalize_text(item.get("form_factor"))
        machine_row.completed_on = completed_on or manifest_date
        machine_row.sku = (
            normalize_text(item.get("sku"))
            or normalize_text(item.get("model"))
            or serial
            or f"machine-{source_machine_id}"
        )
        machine_row.appliance_type = appliance_type
        machine_row.description = description
        machine_row.msrp = parse_optional_cents(
            item.get("msrp_cents"),
            f"machines[{idx}].msrp_cents",
        )
        machine_row.your_cost = parse_optional_cents(
            item.get("your_cost_cents"),
            f"machines[{idx}].your_cost_cents",
        )

        used_machine_ids.add(machine_row.id)

    stale_rows = [
        machine
        for machine in manifest_row.machines
        if machine.id is not None and machine.id not in used_machine_ids
    ]
    for stale_row in stale_rows:
        db.session.delete(stale_row)

    apply_pricing_status(manifest_row)
    db.session.commit()
    return manifest_row, line_number


@manifest.post("/completed_machines")
def build_completed_machines_manifest():
    payload = request.get_json(silent=True) or {}

    try:
        manifest_row, line_number = upsert_completed_machines_manifest(payload)
    except IntegrityError as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[COMPLETED MACHINES BUILD INTEGRITY ERROR]")
        return jsonify(success=False, message=f"Integrity error: {exc.orig}"), 409
    except ValueError as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[COMPLETED MACHINES BUILD VALUE ERROR]")
        return jsonify(success=False, message=str(exc)), 400
    except Exception as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[COMPLETED MACHINES BUILD ERROR]")
        return jsonify(success=False, message=f"Build failed: {exc}"), 500

    return (
        jsonify(
            success=True,
            message="Completed machines manifest built",
            payload={
                "manifest": manifest_row.serialize(include_machines=True),
                "line_items": line_number,
            },
        ),
        201,
    )


@manifest.post("/completed_machines/build_previous_workday")
def build_previous_workday_manifest():
    payload = request.get_json(silent=True) or {}
    source_date_raw = normalize_text(payload.get("source_date"))

    try:
        source_date = (
            parse_optional_date(source_date_raw, "source_date")
            if source_date_raw
            else previous_workday(date.today())
        )
        blutape_payload = fetch_blutape_completed_manifest_payload(source_date)
        if not (blutape_payload.get("machines") or []):
            return (
                jsonify(
                    success=True,
                    message="No unexported completed machines found for source_date",
                    payload={"source_date": source_date.isoformat(), "line_items": 0},
                ),
                200,
            )
        manifest_row, line_number = upsert_completed_machines_manifest(blutape_payload)
        acknowledge_blutape_manifest_export(
            source_date,
            manifest_row.manifest_id,
            blutape_payload.get("machines") or [],
        )
    except ValueError as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[PREVIOUS WORKDAY BUILD VALUE ERROR]")
        return jsonify(success=False, message=str(exc)), 400
    except RuntimeError as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[PREVIOUS WORKDAY BUILD RUNTIME ERROR]")
        return jsonify(success=False, message=str(exc)), 502
    except IntegrityError as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[PREVIOUS WORKDAY BUILD INTEGRITY ERROR]")
        return jsonify(success=False, message=f"Integrity error: {exc.orig}"), 409
    except Exception as exc:
        db.session.rollback()
        MANIFEST_DESTINY.logger.exception("[PREVIOUS WORKDAY BUILD ERROR]")
        return jsonify(success=False, message=f"Build failed: {exc}"), 500

    return (
        jsonify(
            success=True,
            message="Previous workday manifest built",
            payload={
                "source_date": source_date.isoformat(),
                "manifest": manifest_row.serialize(include_machines=True),
                "line_items": line_number,
            },
        ),
        201,
    )


@manifest.get("/completed_machines/count")
def count_completed_machines():
    source_date_raw = normalize_text(request.args.get("source_date"))

    try:
        source_date = (
            parse_optional_date(source_date_raw, "source_date")
            if source_date_raw
            else previous_workday(date.today())
        )
        blutape_payload = fetch_blutape_completed_manifest_payload(source_date)
        machines = blutape_payload.get("machines") or []
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except RuntimeError as exc:
        MANIFEST_DESTINY.logger.exception("[COMPLETED MACHINES COUNT RUNTIME ERROR]")
        return jsonify(success=False, message=str(exc)), 502
    except Exception as exc:
        MANIFEST_DESTINY.logger.exception("[COMPLETED MACHINES COUNT ERROR]")
        return jsonify(success=False, message=f"Count failed: {exc}"), 500

    return (
        jsonify(
            success=True,
            payload={
                "source_date": source_date.isoformat(),
                "count": len(machines),
            },
        ),
        200,
    )


@manifest.get("/")
def manifesto():
    limit = int(request.args.get("limit", "1"))
    include_machines = true_or_false(request.args.get("include_machines"))
    many = true_or_false(request.args.get("many"))
    manifest_id = int(request.args.get("manifest_id", "0"))
    
    query = db.session.query(Manifest)
    payload = {}
    
    if many:
        query = query.limit(limit)
        machines = query.all()
        payload["manifests"] = [m.serialize(include_machines=include_machines) for m in machines]
    else:
        machine = query.get(manifest_id)
        payload["manifest"] = machine.serialize(include_machines=include_machines)
        
    
        
    return jsonify(success=True, payload=payload), 200


@manifest.patch("/machine_prices")
def update_machine_prices():
    payload = request.get_json(silent=True) or {}

    manifest_id = str(payload.get("manifest_id", "")).strip()
    machine_id_raw = payload.get("machine_id")
    lowes_price_raw = payload.get("lowes_price_cents")
    listed_price_raw = payload.get("listed_price_cents")

    if not manifest_id:
        return jsonify(success=False, message="manifest_id is required"), 400
    if machine_id_raw is None:
        return jsonify(success=False, message="machine_id is required"), 400

    try:
        machine_id = int(machine_id_raw)
    except (TypeError, ValueError):
        return jsonify(success=False, message="machine_id must be an integer"), 400

    try:
        lowes_price_cents = parse_optional_cents(lowes_price_raw, "lowes_price_cents")
        listed_price_cents = parse_optional_cents(listed_price_raw, "listed_price_cents")
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400

    machine = db.session.get(Machine, machine_id)
    if not machine:
        return jsonify(success=False, message="Machine not found"), 404

    manifest_row = machine.manifest
    if not manifest_row or manifest_row.manifest_id != manifest_id:
        return jsonify(success=False, message="Machine does not belong to manifest_id"), 400

    machine.lowes_price = lowes_price_cents
    machine.listed_price = listed_price_cents
    apply_pricing_status(manifest_row)
    db.session.commit()

    return (
        jsonify(
            success=True,
            message="Machine prices updated",
            payload={
                "machine": machine.serialize(),
                "manifest_id": manifest_row.manifest_id,
            },
        ),
        200,
    )


@manifest.patch("/machine_prices/batch")
def update_machine_prices_batch():
    payload = request.get_json(silent=True) or {}

    manifest_id = str(payload.get("manifest_id", "")).strip()
    items = payload.get("items")

    if not manifest_id:
        return jsonify(success=False, message="manifest_id is required"), 400
    if not isinstance(items, list) or not items:
        return jsonify(success=False, message="items must be a non-empty array"), 400

    manifest_row = db.session.query(Manifest).filter_by(manifest_id=manifest_id).first()
    if not manifest_row:
        return jsonify(success=False, message="Manifest not found"), 404

    machine_ids = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            return jsonify(success=False, message=f"items[{idx}] must be an object"), 400
        machine_id_raw = item.get("machine_id")
        try:
            machine_id = int(machine_id_raw)
        except (TypeError, ValueError):
            return jsonify(success=False, message=f"items[{idx}].machine_id must be an integer"), 400
        machine_ids.append(machine_id)

    machines = (
        db.session.query(Machine)
        .filter(Machine.id.in_(machine_ids), Machine.manifest_pk == manifest_row.id)
        .all()
    )
    machine_map = {m.id: m for m in machines}

    if len(machine_map) != len(set(machine_ids)):
        return jsonify(success=False, message="One or more machines do not belong to manifest_id"), 400

    try:
        for item in items:
            machine_id = int(item["machine_id"])
            machine = machine_map[machine_id]
            machine.lowes_price = parse_optional_cents(
                item.get("lowes_price_cents"),
                f"machine[{machine_id}].lowes_price_cents",
            )
            machine.listed_price = parse_optional_cents(
                item.get("listed_price_cents"),
                f"machine[{machine_id}].listed_price_cents",
            )
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400

    apply_pricing_status(manifest_row)
    db.session.commit()

    return (
        jsonify(
            success=True,
            message="Machine prices updated",
            payload={
                "manifest_id": manifest_row.manifest_id,
                "machines": [m.serialize() for m in machines],
            },
        ),
        200,
    )


@manifest.get("/status_options")
def get_manifest_status_options():
    return (
        jsonify(
            success=True,
            payload={"status_options": [status.value for status in ManifestStatusEnum]},
        ),
        200,
    )


@manifest.patch("/status")
def update_manifest_status():
    payload = request.get_json(silent=True) or {}
    manifest_id = str(payload.get("manifest_id", "")).strip()
    status_raw = str(payload.get("status", "")).strip().lower()

    if not manifest_id:
        return jsonify(success=False, message="manifest_id is required"), 400
    if not status_raw:
        return jsonify(success=False, message="status is required"), 400

    valid_statuses = {status.value for status in ManifestStatusEnum}
    if status_raw not in valid_statuses:
        return (
            jsonify(
                success=False,
                message=f"status must be one of: {', '.join(sorted(valid_statuses))}",
            ),
            400,
        )

    manifest_row = db.session.query(Manifest).filter_by(manifest_id=manifest_id).first()
    if not manifest_row:
        return jsonify(success=False, message="Manifest not found"), 404

    manifest_row.status = ManifestStatusEnum(status_raw)
    db.session.commit()

    return (
        jsonify(
            success=True,
            message="Manifest status updated",
            payload={
                "manifest_id": manifest_row.manifest_id,
                "status": manifest_row.status.value,
            },
        ),
        200,
    )


@manifest.patch("/metadata")
def update_manifest_metadata():
    payload = request.get_json(silent=True) or {}
    manifest_id = str(payload.get("manifest_id", "")).strip()

    if not manifest_id:
        return jsonify(success=False, message="manifest_id is required"), 400

    incoming_manifest_id = payload.get("manifest_id_new")
    incoming_truck_id = payload.get("truck_id")
    has_arrival_date = "truck_arrival_date" in payload
    has_manifest_update = incoming_manifest_id is not None
    has_truck_update = incoming_truck_id is not None

    if not (has_arrival_date or has_manifest_update or has_truck_update):
        return (
            jsonify(
                success=False,
                message="At least one of truck_arrival_date, manifest_id_new, or truck_id is required",
            ),
            400,
        )

    manifest_row = db.session.query(Manifest).filter_by(manifest_id=manifest_id).first()
    if not manifest_row:
        return jsonify(success=False, message="Manifest not found"), 404

    if has_manifest_update:
        next_manifest_id = str(incoming_manifest_id or "").strip()
        if not next_manifest_id:
            return jsonify(success=False, message="manifest_id_new must be non-empty"), 400
        manifest_row.manifest_id = next_manifest_id

    if has_truck_update:
        next_truck_id = str(incoming_truck_id or "").strip()
        if not next_truck_id:
            return jsonify(success=False, message="truck_id must be non-empty"), 400
        manifest_row.truck_id = next_truck_id

    if has_arrival_date:
        truck_arrival_date_raw = payload.get("truck_arrival_date")
        if truck_arrival_date_raw in (None, ""):
            manifest_row.truck_arrival_date = None
        else:
            try:
                manifest_row.truck_arrival_date = date.fromisoformat(
                    str(truck_arrival_date_raw).strip()
                )
            except ValueError:
                return jsonify(success=False, message="truck_arrival_date must be YYYY-MM-DD or null"), 400

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, message="manifest_id already exists"), 409

    return (
        jsonify(
            success=True,
            message="Manifest metadata updated",
            payload={
                "manifest": manifest_row.serialize(include_machines=False),
            },
        ),
        200,
    )


@manifest.delete("/<int:manifest_pk>")
def delete_manifest(manifest_pk: int):
    manifest_row = db.session.get(Manifest, manifest_pk)
    if not manifest_row:
        return jsonify(success=False, message="Manifest not found"), 404

    try:
        manifest_id = manifest_row.manifest_id
        db.session.delete(manifest_row)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify(success=False, message=f"Failed to delete manifest: {exc}"), 500

    return (
        jsonify(
            success=True,
            message="Manifest deleted",
            payload={"id": manifest_pk, "manifest_id": manifest_id},
        ),
        200,
    )


@manifest.get("/<int:manifest_pk>/export.csv")
def export_manifest_csv(manifest_pk: int):
    manifest_row = db.session.get(Manifest, manifest_pk)
    if not manifest_row:
        return jsonify(success=False, message="Manifest not found"), 404

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "manifest_id",
            "truck_id",
            "manufacturer",
            "status",
            "truck_arrival_date",
            "line_number",
            "sku",
            "appliance_type",
            "description",
            "msrp",
            "your_cost",
            "listed_price",
            "lowes_price",
        ]
    )

    for machine in sorted(manifest_row.machines, key=lambda m: m.line_number):
        writer.writerow(
            [
                manifest_row.manifest_id,
                manifest_row.truck_id,
                manifest_row.manufacturer,
                manifest_row.status.value,
                manifest_row.truck_arrival_date.isoformat()
                if manifest_row.truck_arrival_date
                else "",
                machine.line_number,
                machine.sku,
                machine.appliance_type,
                machine.description,
                cents_to_decimal_str(machine.msrp) or "",
                cents_to_decimal_str(machine.your_cost) or "",
                cents_to_decimal_str(machine.listed_price) or "",
                cents_to_decimal_str(machine.lowes_price) or "",
            ]
        )

    csv_data = buffer.getvalue()
    buffer.close()

    safe_manifest_id = str(manifest_row.manifest_id).replace(" ", "_")
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'attachment; filename="manifest_{safe_manifest_id}.csv"',
        },
    )


@manifest.get("/all")
def get_all_manifests():
    manifests = db.session.query(Manifest).limit(5).all()
    includes_machines = true_or_false(request.args.get("include_machines"))
    return jsonify(success=True, manifests=[m.serialize(include_machines=includes_machines) for m in manifests]), 200


@manifest.get("/id/int:manifest_id")
def get_manifest_by_id(manifest_id):
    print(manifest_id)
    manifest = db.session.get(Manifest, manifest_id)
    if not manifest:
        return jsonify(success=False, message="Manifest not found"), 400
    
    return jsonify(success=True, manifest=manifest.serialize(include_machines=True)), 200

@manifest.get("/by_date")
def get_manifest_by_date():
    pass

@manifest.get("/by_truck_id")
def get_manifest_by_truck_id():
    pass

@manifest.get("/by_status")
def get_manifest_by_status():
    pass
