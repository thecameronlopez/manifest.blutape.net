from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base



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
    
    sku: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    appliance_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    
    msrp: Mapped[int] = mapped_column(Integer, nullable=False)
    your_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    
    listed_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lowes_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    manifest = relationship("Manifest", back_populates="machines")
    
    
    def suggested_price(self, multiplier: str) -> int:
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