import enum
from datetime import date as DTdate

from sqlalchemy import String, Integer, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class ManifestStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PRICED = "priced"
    COMPLETED = "completed"
    

class Manifest(Base):
    __tablename__ = "manifests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    truck_arrival_date: Mapped[DTdate | None] = mapped_column(Date, nullable=True, index=True)
    
    truck_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    manifest_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    status: Mapped[ManifestStatusEnum] = mapped_column(
        Enum(ManifestStatusEnum, native_enum=False), 
        default=ManifestStatusEnum.PENDING, 
        nullable=False,
        index=True
    )
    
    completed_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_on: Mapped[DTdate] = mapped_column(Date, nullable=False, default=DTdate.today)
    updated_on: Mapped[DTdate] = mapped_column(Date, nullable=False, default=DTdate.today, onupdate=DTdate.today)
    
    machines = relationship(
        "Machine", 
        back_populates="manifest", 
        cascade="all, delete-orphan", 
        lazy="selectin"
    )
    
    
    def serialize(self, include_machines:bool =False) -> dict:
          return {
              "id": self.id,
              "truck_arrival_date": self.truck_arrival_date.isoformat() if self.truck_arrival_date else None,
              "truck_id": self.truck_id,
              "manifest_id": self.manifest_id,
              "manufacturer": self.manufacturer,
              "status": self.status.value,
              "completed_file_path": self.completed_file_path,
              "created_on": self.created_on.strftime("%Y-%m-%d"),
              "machines": [m.serialize() for m in self.machines] if include_machines else None
          }
