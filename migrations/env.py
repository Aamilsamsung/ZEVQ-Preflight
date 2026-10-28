import os
from alembic import context
from app.db import Base, make_engine
engine = make_engine(os.getenv("DATABASE_URL_UNPOOLED") or None)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
