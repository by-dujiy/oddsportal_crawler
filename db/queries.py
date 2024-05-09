from sqlalchemy import select
from .db import Session
from .db_models import EventRow


session = Session()


def get_eventrow_url(row_id):
    row = select(EventRow).where(EventRow.id == 1)
    return session.scalar(row).event_url
