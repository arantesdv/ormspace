from contextlib import asynccontextmanager

from ormspace.alias import QUERIES, QUERY
from ormspace.bases import ModelType


@asynccontextmanager
async def load_queries_context(model: type[ModelType], queries: QUERIES):
    await model.update_dependencies_context(queries=queries)
    yield
    
@asynccontextmanager
async def load_query_context(model: type[ModelType], query: QUERY):
    await model.update_model_context(query=query)
    yield
    