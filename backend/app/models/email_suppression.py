from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailSuppression(Base):
    """Adresse a ne plus solliciter, apres un rebond dur ou une plainte.

    Voir `app/services/email_suppression.py` pour le pourquoi. L'adresse est
    stockee en minuscules pour que la comparaison soit fiable : les serveurs de
    messagerie ne distinguent pas la casse de la partie locale en pratique, mais
    un utilisateur qui saisit `Jean.Dupont@` puis `jean.dupont@` creerait deux
    entrees et l'une des deux ne bloquerait rien.
    """

    __tablename__ = "email_suppressions"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # `email.bounced` ou `email.complained`
    evenement: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    constate_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
