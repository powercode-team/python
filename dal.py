"""Search sessions DAL."""
import datetime
from typing import Any, AsyncGenerator, Sequence

from sqlalchemy import exists, ScalarResult, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.db.config import async_session, Base
from app.db.dal import BaseDAL
from app.propositions.models import Proposition
from app.search_sessions.models import Filters, Locations, SearchSession


class SearchSessionsDAL(BaseDAL):
    """Search sessions DAL."""

    model: Base = SearchSession

    async def create(
        self,
        data: dict,
        entity: Base | None = None,
    ) -> SearchSession:
        """Create search session."""
        filters_data: Filters | None = data.pop("filters", None)
        propositions: list[Proposition] | None = data.pop("propositions", None)
        search_session: SearchSession = self.model(**data)

        # add filters to the search session
        if filters_data:
            search_session.filters = Filters(
                locations=[Locations(**i) for i in filters_data.pop("locations", [])],
                **filters_data,
            )

        # add propositions to the search session
        if propositions:
            search_session.propositions = Proposition.from_list(data=propositions)  # type: ignore

        self.db_session.add(search_session)
        await self.db_session.flush()
        return search_session

    async def exist(self, session_id: int) -> bool:
        """Check if search session exist."""
        return await self.db_session.scalar(
            exists().where(SearchSession.id == session_id).select(),
        )

    async def is_session_closed(self, session_id: int) -> bool | None:
        """Check if session is closed."""
        query = select(self.model.is_closed).where(self.model.id == session_id)
        return await self.db_session.scalar(query)

    async def add_propositions(
        self,
        propositions: Sequence[Any],
        search_session: SearchSession | None = None,
        search_session_id: int | None = None,
    ) -> SearchSession | None:
        """
        Add propositions to the session.
        Logic:
            - if proposition exist for the current SearchSession - ignore it,
            - if proposition with this internal_id already exists in DB - add it
            to the current SearchSession
            - if proposition is not exist - create it and add to the current SearchSession
        """

        query: Select = (
            select(self.model)
            .where(self.model.id == search_session_id)
            .options(selectinload(self.model.propositions))
        )

        if not search_session and search_session_id:
            # get search session
            search_session = await self.db_session.scalar(query)

        propositions_internal_ids: list[int | None] = [p.internal_id for p in propositions]

        # select all existed propositions
        existed_propositions = (
            await self.db_session.scalars(
                select(Proposition).where(Proposition.internal_id.in_(propositions_internal_ids))
            )
        ).all()

        # now there is only filtered new propositions
        new_propositions = [
            p
            for p in propositions
            if p.internal_id not in [ep.internal_id for ep in existed_propositions]
        ]

        # now add existed propositions
        for p in existed_propositions:
            # add proposition to the session
            # if this proposition does not related to the current session
            if (
                search_session
                and search_session.propositions is not None
                and search_session.id not in [i.id for i in p.search_sessions]
            ):
                search_session.propositions.append(p)

        # cast new propositions to Proposition model with price comparisons
        new_propositions = Proposition.from_list(
            data=[np.dict() for np in new_propositions]
        )  # type: ignore

        # add new proposition
        if search_session and search_session.propositions:
            search_session.propositions += new_propositions

        elif search_session and not search_session.propositions:
            search_session.propositions = new_propositions

        if search_session:
            search_session.updated_at = datetime.datetime.now()
        # save search session
        self.db_session.add(search_session)
        await self.db_session.commit()
        await self.db_session.flush()
        return search_session

    async def get_by_filters(
        self,
        dispatcher_id: int,
        filters_data: str | None,
    ) -> Sequence[Any] | None:
        """Get search session for dispatcher by provided filters data."""

        query: Select = select(self.model)
        if dispatcher_id:
            # add where clause on dispatcher_id
            query = query.where(
                SearchSession.dispatcher_id == dispatcher_id,
            )
            if filters_data:
                # add where clause on filters_string
                query = query.where(
                    SearchSession.filters_string == filters_data,
                )
                result: ScalarResult = await self.db_session.scalars(query)
                return result.all()

        return None


async def get_search_sessions_dal() -> AsyncGenerator:
    """Get search sessions DAL with DB session."""
    async with async_session() as session:
        async with session.begin():
            yield SearchSessionsDAL(session)
