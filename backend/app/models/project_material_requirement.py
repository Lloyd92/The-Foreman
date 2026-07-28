from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProjectMaterialRequirement(Base):
    __tablename__ = "project_material_requirements"
    __table_args__ = (
        Index(
            "ix_project_material_requirements_inventory_item_id",
            "inventory_item_id",
        ),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    inventory_item_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    required_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    project: Mapped["Project"] = relationship(
        back_populates="material_requirements",
    )
