from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VaultItem(Base):
    __tablename__ = "vault_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Legacy plaintext fields (nullable — only populated for pre-ZK legacy items)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Encrypted fields (zero-knowledge — backend stores opaque blobs)
    title_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    username_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Always encrypted
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="login", server_default="login"
    )
