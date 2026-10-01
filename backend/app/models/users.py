from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, OriginMixin, TimestampMixin


class Role(Base):
    __tablename__ = "roles"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # worker | assessor | admin
    label: Mapped[str] = mapped_column(String(64))


class User(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "users"
    login: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # email or mobile
    password_hash: Mapped[str] = mapped_column(String(128))
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    assessor_code: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped[Role] = relationship(lazy="joined")
