"""Search sessions schemas."""

from datetime import date, datetime

from pydantic.fields import Field
from pydantic.main import BaseModel
from pydantic.types import Decimal

from app.propositions.schemas import (
    DispatcherPropositionsResponse,
    PropositionRequest,
    PropositionResponse,
)


class LocationsRequest(BaseModel):
    """Location request model."""

    address: str | None = Field(None, max_length=128)
    radius: int | None
    scope: str | None = Field(None, max_length=16)

    class Config:
        orm_mode = True


class FiltersRequest(BaseModel):
    """Filter request model."""

    vehicle_type: list[str] | None
    vehicle_status: str | None
    min_vehicles_num: int | None
    max_vehicles_num: int | None
    delivery_date: date | None
    min_total_pay: Decimal | None
    min_rate: Decimal | None
    locations: list[LocationsRequest]


class FiltersResponse(FiltersRequest):
    """Filter response model."""

    id: int

    class Config:
        orm_mode = True


class DispatcherFilterResponse(BaseModel):
    """Filter response model for dispatcher."""

    locations: list[LocationsRequest]

    class Config:
        orm_mode = True


class SearchSessionCheckRequest(BaseModel):
    """Check search session request model."""

    dispatcher_id: int
    filters: FiltersRequest


class SearchSessionRequest(BaseModel):
    """Search session request model."""

    dispatcher_id: int
    created_at: datetime | None
    is_closed: bool = False
    type: str
    filters: FiltersRequest


class SearchSessionBaseResponse(BaseModel):
    """Search session base response model."""

    id: int


class SearchSessionResponse(SearchSessionBaseResponse):
    """Search session response model."""

    type: str
    is_closed: bool
    extra_load: bool

    class Config:
        orm_mode = True


class SearchSessionPropositionsRequest(BaseModel):
    """Model for adding propositions to search session request."""

    propositions: list[PropositionRequest]
    extra_load: bool = False


class SearchSessionPropositionsResponse(SearchSessionResponse):
    """Model for adding propositions to search session response."""

    propositions: list[PropositionResponse] | None


class PropositionWithoutComparisons(BaseModel):
    """Model for data of proposition which have no price comparisons."""

    id: int
    internal_id: int


class SearchSessionWithoutComparisons(BaseModel):
    """Response model for Search session without price comparisons in propositions."""

    search_session: SearchSessionPropositionsResponse
    propositions_without_comparisons: list[PropositionWithoutComparisons]


class DispatcherPropositionsEventResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class DispatcherPropositionRelationResponse(BaseModel):
    proposition_id: int
    events: list[DispatcherPropositionsEventResponse] | None

    class Config:
        orm_mode = True


class DispatcherSearchSessionsListResponse(SearchSessionResponse):
    """Dispatcher's active sessions list response."""

    created_at: datetime
    updated_at: datetime
    filters: DispatcherFilterResponse
    propositions: list[DispatcherPropositionsResponse] | None
    expanded_event_num: int
    interested_event_num: int
    call_event_num: int
    proposition_relations: list[DispatcherPropositionRelationResponse] | None


class DispatcherSearchSessionsIdsList(SearchSessionBaseResponse):
    """Dispatcher's active sessions ids list response."""

    filters: DispatcherFilterResponse

    class Config:
        orm_mode = True


class CloseSearchSessionRequest(BaseModel):
    """Model for closing session request."""

    is_successful: bool
    proposition_internal_id: int | None
    reason: str | None
    is_closed: bool


class CloseSearchSessionResponse(SearchSessionResponse):
    """Model for closing session response."""

    is_successful: bool
