from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from werkzeug.utils import secure_filename

ManifestType = Literal["new", "priced", "completed"]
SuffixType = Literal["raw", "priced", "completed"]

@dataclass(frozen=True)
class ResolvedUploadPath:
    absolute_dir: Path
    absolute_file: Path
    relative_path: str
    filename: str
    

def _normalize_part(value: str) -> str:
    cleaned = secure_filename((value or "").strip().lower())
    return cleaned or "unknown"


def _coerce_date(value: date | datetime | str | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value.strip())


def resolve_upload_path(
    upload_root: str | Path,
    manifest_type: ManifestType,
    manifest_date: date | datetime | str | None,
    truck_id: str,
    manifest_id: str,
    manufacturer: str,
    suffix: SuffixType,
) -> ResolvedUploadPath:
    d = _coerce_date(manifest_date)
    year = str(d.year)
    
    truck = _normalize_part(truck_id)
    manifest = _normalize_part(manifest_id)
    maker = _normalize_part(manufacturer)
    
    filename = secure_filename(f"{d.isoformat()}_{truck}_{manifest}_{maker}_{suffix}.csv")
    target_dir = Path(upload_root) / manifest_type / year
    absolute_file = target_dir / filename
    relative_path = f"{manifest_type}/{year}/{filename}"
    
    return ResolvedUploadPath(
        absolute_dir=target_dir,
        absolute_file=absolute_file,
        relative_path=relative_path,
        filename=filename,
    )
    

def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)