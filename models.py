"""Search sessions DB models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic.types import Decimal
from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from app.db.models import BaseModel


class SearchSessionsPropositionsEvents(BaseModel):
    """Model for M2M relation between search_sessions_propositions and events."""

    __tablename__ = "search_sessions_propositions_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    search_sessions_propositions_id: Mapped[int] = mapped_column(
        ForeignKey("search_sessions_propositions.id"),
    )
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))

    # relation between SearchSessionsPropositionsEvents -> Event
    event: Mapped["Event"] = relationship(  # type: ignore
        back_populates="search_sessions_propositions_relations",
    )

    # relation between SearchSessionsPropositionsEvents -> SearchSessionsPropositions
    search_session_proposition: Mapped["SearchSessionsPropositions"] = relationship(  # type: ignore
        back_populates="event_relations",
    )


class SearchSessionsPropositions(BaseModel):
    """Model for M2M relation between search session and proposition."""

    __tablename__ = "search_sessions_propositions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    search_session_id: Mapped[int] = mapped_column(ForeignKey("search_sessions.id"))
    proposition_id: Mapped[int] = mapped_column(ForeignKey("propositions.id"))

    # relation between SearchSessionsPropositions -> Proposition
    proposition: Mapped["Proposition"] = relationship(  # type: ignore
        back_populates="search_session_relations",
    )

    # relation between SearchSessionsPropositions -> SearchSession
    search_session: Mapped["SearchSession"] = relationship(back_populates="proposition_relations")

    # m2m relationship to Event, bypassing the `SearchSessionsPropositionsEvents` class
    events: Mapped[list["Event"]] = relationship(  # type: ignore
        secondary="search_sessions_propositions_events",
        back_populates="search_sessions_propositions",
        lazy="selectin",
    )

    # relation between SearchSessionsPropositions -> SearchSessionsPropositionsEvents -> Event
    event_relations: Mapped[list["SearchSessionsPropositionsEvents"]] = relationship(
        back_populates="search_session_proposition",
        lazy="selectin",
    )


class SearchSession(BaseModel):
    """Search session model."""

    __tablename__ = "search_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dispatcher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dispatchers.id", ondelete="SET NULL"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    extra_load: Mapped[bool] = mapped_column(default=False)
    is_successful: Mapped[bool] = mapped_column(default=False, server_default=expression.false())
    reason: Mapped[Optional[str]] = mapped_column(String(256))
    is_closed: Mapped[bool] = mapped_column(default=False, server_default=expression.false())
    type: Mapped[str] = mapped_column(default="real", server_default="real")
    filters_string: Mapped[str | None] = mapped_column(String(1024))

    # relations
    dispatcher: Mapped[Literal["Dispatcher"]] = relationship()
    filters: Mapped["Filters"] = relationship(back_populates="search_session", lazy="selectin")

    # m2m relation between search sessions and propositions
    propositions: Mapped[list["Proposition"]] = relationship(  # type: ignore
        secondary="search_sessions_propositions",
        back_populates="search_sessions",
        lazy="selectin",
    )

    # relation between SearchSession -> SearchSessionsPropositions -> Proposition
    proposition_relations: Mapped[list["SearchSessionsPropositions"]] = relationship(
        back_populates="search_session", lazy="selectin"
    )


class Filters(BaseModel):
    """Search filters model."""

    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    search_session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("search_sessions.id", ondelete="SET NULL"),
        index=True,
    )
    vehicle_type: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(32)))
    vehicle_status: Mapped[Optional[str]] = mapped_column(String(32))
    min_vehicles_num: Mapped[Optional[int]]
    max_vehicles_num: Mapped[Optional[int]]
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    min_total_pay: Mapped[Optional[Decimal]] = mapped_column(Numeric)
    min_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric)

    # relation
    search_session: Mapped["SearchSession"] = relationship(back_populates="filters")
    locations: Mapped[list[Locations]] = relationship(
        back_populates="filters",
        lazy="selectin",
    )


class Locations(BaseModel):
    """Filters locations model."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(128))
    radius: Mapped[Optional[int]]
    scope: Mapped[str] = mapped_column(String(16))

    filters_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("filters.id", ondelete="SET NULL"),
        index=True,
    )

    # relation
    filters: Mapped["Filters"] = relationship(back_populates="locations")
