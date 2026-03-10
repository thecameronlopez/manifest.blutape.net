import enum
from datetime import date as DTdate
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Enum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class MachineEntryKindEnum(str, enum.Enum):
    INVENTORY = "inventory"
    BLUTAPE_COMPLETION = "blutape_completion"


class Machine(Base):
    __tablename__ = "machines"

    __table_args__ = (
        UniqueConstraint(
            "manifest_pk",
            "line_number",
            name="uq_machine_manifest_line"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    manifest_pk: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("manifests.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )

    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    entry_kind: Mapped[MachineEntryKindEnum] = mapped_column(
        Enum(
            MachineEntryKindEnum,
            native_enum=False,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        default=MachineEntryKindEnum.INVENTORY,
        nullable=False,
        index=True,
    )
    source_machine_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_work_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    serial: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    form_factor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed_on: Mapped[DTdate | None] = mapped_column(Date, nullable=True, index=True)

    sku: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    appliance_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)

    msrp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    your_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)

    listed_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lowes_price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    manifest = relationship("Manifest", back_populates="machines")

    def suggested_price(self, multiplier: str) -> int:
        if self.your_cost is None:
            return 0
        return int(
            (Decimal(self.your_cost) * Decimal(multiplier))
            .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

    @property
    def price_75(self) -> int:
        return self.suggested_price("1.75")

    @property
    def price_100(self) -> int:
        return self.suggested_price("2.00")

    @property
    def price_125(self) -> int:
        return self.suggested_price("2.25")

    @property
    def price_150(self) -> int:
        return self.suggested_price("2.50")

    @property
    def price_175(self) -> int:
        return self.suggested_price("2.75")

    @property
    def price_200(self) -> int:
        return self.suggested_price("3.00")

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "manifest_pk": self.manifest_pk,
            "line_number": self.line_number,
            "entry_kind": self.entry_kind.value,
            "source_machine_id": self.source_machine_id,
            "source_work_order_id": self.source_work_order_id,
            "source_event_id": self.source_event_id,
            "serial": self.serial,
            "brand": self.brand,
            "model": self.model,
            "vendor": self.vendor,
            "condition": self.condition,
            "color": self.color,
            "form_factor": self.form_factor,
            "completed_on": self.completed_on.isoformat() if self.completed_on else None,
            "sku": self.sku,
            "appliance_type": self.appliance_type,
            "description": self.description,
            "msrp": self.msrp,
            "your_cost": self.your_cost,
            "listed_price": self.listed_price if self.listed_price is not None else None,
            "lowes_price": self.lowes_price if self.lowes_price is not None else None,
            "markup_75": self.price_75,
            "markup_100": self.price_100,
            "markup_125": self.price_125,
            "markup_150": self.price_150,
            "markup_175": self.price_175,
            "markup_200": self.price_200
        }
