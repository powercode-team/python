"""Search sessions routes."""
from logging import basicConfig, getLogger, INFO, Logger
from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.dispatchers.models import Dispatcher
from app.events.models import Event
from app.exceptions import EntityDoesNotExist
from app.propositions.models import Proposition
from app.search_sessions.dal import get_search_sessions_dal, SearchSessionsDAL
from app.search_sessions.models import (
    SearchSession,
    SearchSessionsPropositions,
    SearchSessionsPropositionsEvents,
)
from app.search_sessions.schemas import (
    CloseSearchSessionRequest,
    CloseSearchSessionResponse,
    DispatcherSearchSessionsListResponse,
    SearchSessionCheckRequest,
    SearchSessionPropositionsRequest,
    SearchSessionRequest,
    SearchSessionResponse,
    SearchSessionWithoutComparisons,
)

basicConfig(level=INFO)
logger: Logger = getLogger(__name__)

search_sessions_router: APIRouter = APIRouter()


def filters_data_to_string(input_data: dict) -> str:
    """Convert dict filters data to string."""
    filters_data: dict = input_data.get("filters", {})
    locations_data: list[dict] = filters_data.get("locations", [])
    filters_data_copied = filters_data.copy()
    filters_data_copied["locations"] = sorted(
        locations_data, key=lambda d: (d["address"], d["scope"])
    )
    return str(filters_data_copied)


@search_sessions_router.get(
    path="/search_sessions/{search_session_id}/",
    tags=["search sessions"],
    name="Get search session",
    response_model=SearchSessionResponse,
    description="Get search session data.",
)
async def get(
    search_session_id: int,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> SearchSessionResponse:
    """Get search session by provided ID."""
    # check if search session exists
    search_session: SearchSession | None = await dal.get(search_session_id)

    if not search_session:
        raise EntityDoesNotExist(detail="Search session not found.")

    return search_session


@search_sessions_router.get(
    path="/search_sessions/{search_session_id}/details/",
    tags=["search sessions"],
    name="Get search session details.",
    response_model=DispatcherSearchSessionsListResponse,
    description="Get search session details.",
)
async def get_details(
    search_session_id: int,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> SearchSessionResponse:
    """Get search session by provided ID."""
    # check if search session exists
    search_session: SearchSession | None = await dal.get(search_session_id)

    if not search_session:
        raise EntityDoesNotExist(detail="Search session not found.")

    expanded_event: Any = await dal.get_by_parameter_values(
        parameter_name="name",
        parameter_values=["expanded"],
        entity=Event,
        single=True,
    )
    interested_event: Any = await dal.get_by_parameter_values(
        parameter_name="name",
        parameter_values=["interested"],
        entity=Event,
        single=True,
    )
    call_event: Any = await dal.get_by_parameter_values(
        parameter_name="name",
        parameter_values=["call"],
        entity=Event,
        single=True,
    )
    expanded_event_num: int = 0
    interested_event_num: int = 0
    call_event_num: int = 0
    # get list of relations ids
    proposition_relations_ids: list[int] | None = [
        p.id for p in search_session.proposition_relations if search_session.proposition_relations
    ]
    if proposition_relations_ids:
        for i in proposition_relations_ids:
            if expanded_event:
                # count all expanded events for relation id
                expanded_event_num += len(
                    await dal.get_by_list_of_parameters(
                        parameter_names=["search_sessions_propositions_id", "event_id"],
                        parameter_values=[i, expanded_event.id],
                        entity=SearchSessionsPropositionsEvents,
                    )
                )
            if interested_event:
                # count all interested events for relation id
                interested_event_num += len(
                    await dal.get_by_list_of_parameters(
                        parameter_names=["search_sessions_propositions_id", "event_id"],
                        parameter_values=[i, interested_event.id],
                        entity=SearchSessionsPropositionsEvents,
                    )
                )
            if call_event:
                # count all interested events for relation id
                call_event_num += len(
                    await dal.get_by_list_of_parameters(
                        parameter_names=["search_sessions_propositions_id", "event_id"],
                        parameter_values=[i, call_event.id],
                        entity=SearchSessionsPropositionsEvents,
                    )
                )
    # added fields with numbers of events to search session object
    search_session.expanded_event_num = expanded_event_num
    search_session.interested_event_num = interested_event_num
    search_session.call_event_num = call_event_num

    return search_session


@search_sessions_router.post(
    path="/search_sessions/check/",
    tags=["search sessions"],
    name="Check search session",
    response_model=SearchSessionResponse,
    description="Check search session by filters data.",
)
async def check(
    payload: SearchSessionCheckRequest,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> SearchSessionResponse:
    """Check search session by filters data."""
    # check if dispatcher exists
    dispatcher_exists: bool = await dal.check_if_exists(
        entity_id=payload.dispatcher_id,
        entity=Dispatcher,
    )

    if not dispatcher_exists:
        raise EntityDoesNotExist(detail="Dispatcher does not exist.")

    #  check is that session is already exist by provided filters
    input_data: dict = payload.dict()

    search_sessions: Sequence[Any] | None = await dal.get_by_filters(
        dispatcher_id=input_data["dispatcher_id"],
        filters_data=filters_data_to_string(input_data=input_data),
    )
    active_search_session: SearchSession | None = None
    if search_sessions:
        for s in search_sessions:
            if not s.is_closed:
                active_search_session = s

    if not active_search_session:
        raise EntityDoesNotExist(detail="Session does not exist.")

    return active_search_session  # type: ignore


@search_sessions_router.post(
    path="/search_sessions/",
    tags=["search sessions"],
    name="Create search session",
    response_model=SearchSessionResponse,
    description="Create search session from provided data.",
)
async def create(
    payload: SearchSessionRequest,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> SearchSessionResponse:
    """Create search session from provided data."""
    # check if dispatcher exists
    dispatcher_exists: bool = await dal.check_if_exists(
        entity_id=payload.dispatcher_id,
        entity=Dispatcher,
    )

    if not dispatcher_exists:
        raise EntityDoesNotExist(detail="Dispatcher does not exist.")

    input_data: dict = payload.dict()
    input_data["filters_string"] = filters_data_to_string(input_data=input_data)

    search_sessions: Sequence[Any] | None = await dal.get_by_filters(
        dispatcher_id=input_data["dispatcher_id"],
        filters_data=input_data["filters_string"],
    )
    if search_sessions:
        active_search_session: SearchSession | None = next(
            (s for s in search_sessions if not s.is_closed), None
        )

        if active_search_session:
            detail: str = "A session with these filters has already been created."
            logger.error(f"Error: {detail}")
            raise HTTPException(
                status_code=400,
                detail=detail,
            )
    return await dal.create(data=input_data)


@search_sessions_router.post(
    path="/search_sessions/{search_session_id}/propositions/",
    tags=["search sessions"],
    name="Add propositions to the search session",
    response_model=SearchSessionWithoutComparisons,
    description="Add propositions to the existed search session.",
)
async def add_propositions(
    search_session_id: int,
    payload: SearchSessionPropositionsRequest,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> SearchSessionWithoutComparisons:
    """Add propositions to the existed search session."""
    # check if search session exists
    search_session_exists: bool = await dal.exist(search_session_id)
    if not search_session_exists:
        raise EntityDoesNotExist(detail="Search session does not exist.")

    # check if session is closed
    is_closed = await dal.is_session_closed(search_session_id)

    if is_closed:
        detail: str = "Sessions is closed."
        logger.error(f"Error: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    # update extra_load field
    await dal.update_by_id(
        entity_id=search_session_id,
        data={"extra_load": payload.extra_load},
    )
    search_session: SearchSession | None = await dal.add_propositions(
        propositions=payload.propositions,
        search_session_id=search_session_id,
    )

    # filter search_session.propositions with empty price_comparisons
    propositions_without_comparisons: list = []
    if search_session and search_session.propositions:
        propositions_without_comparisons = [
            {
                "id": p.id,
                "internal_id": p.internal_id,
            }
            for p in search_session.propositions
            if not p.price_comparisons
        ]

    return SearchSessionWithoutComparisons(
        search_session=search_session,
        propositions_without_comparisons=propositions_without_comparisons,
    )


@search_sessions_router.patch(
    path="/search_sessions/{search_session_id}/",
    tags=["search sessions"],
    name="Close search session",
    response_model=CloseSearchSessionResponse,
    description="Close opened search session.",
)
async def close_session(
    search_session_id: int,
    payload: CloseSearchSessionRequest,
    dal: SearchSessionsDAL = Depends(get_search_sessions_dal),
) -> CloseSearchSessionResponse:
    search_session: SearchSession | None = await dal.get(search_session_id)

    if not search_session:
        raise EntityDoesNotExist(detail="Search session does not exist.")

    # check if session is closed
    is_closed: bool | None = await dal.is_session_closed(search_session_id)
    detail: str | None = None

    if is_closed:
        detail = "Sessions is closed."
        logger.error(f"Error: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    is_successful: bool = payload.is_successful
    proposition_internal_id: int | None = payload.proposition_internal_id

    if is_successful and not proposition_internal_id:
        detail = "A successful session needs even one accepted proposition."
        logger.error(f"Error: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    if is_successful and proposition_internal_id:
        # check if proposition exists and get it
        proposition: Any = await dal.get_by_parameter_values(
            parameter_name="internal_id",
            parameter_values=[proposition_internal_id],
            single=True,
            entity=Proposition,
        )

        if not proposition:
            raise EntityDoesNotExist(detail="Proposition does not exist.")

        # get proposition relation with search session
        search_sessions_rel: SearchSessionsPropositions | None = await dal.db_session.scalar(
            select(SearchSessionsPropositions).where(
                SearchSessionsPropositions.search_session_id == search_session_id,
                SearchSessionsPropositions.proposition_id == proposition.id,
            )
        )

        if not search_sessions_rel:
            raise EntityDoesNotExist(
                detail="This proposition is not a part of specified search session.",
            )

        # check if event exists and get it
        event: Event = await dal.get_by_parameter_values(  # type: ignore
            parameter_name="name",
            parameter_values=["contracted"],
            single=True,
            entity=Event,
        )

        if not event:
            event = Event(**{"name": "contracted"})
            dal.db_session.add(event)
            await dal.db_session.flush()

        if event.id not in [e.id for e in search_sessions_rel.events]:
            rel = SearchSessionsPropositionsEvents(
                search_sessions_propositions_id=search_sessions_rel.id,
                event_id=event.id,
            )
            dal.db_session.add(rel)
            await dal.db_session.flush()

    data: dict = payload.dict()
    data.pop("proposition_internal_id")

    return await dal.update(search_session, data)
