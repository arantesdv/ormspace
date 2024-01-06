from contextlib import asynccontextmanager

from ormspace.alias import QUERIES, QUERY
from ormspace.bases import ModelType
from anyio import create_task_group


@asynccontextmanager
async def query_context(queries: dict[type[ModelType], QUERY]):
    async with create_task_group() as tks:
        for model in queries.keys():
            tks.start_soon(model.update_model_context, False, queries.get(model, None))
    yield
    

    