from sqlalchemy import select
from .db import Session
from .db_models import EventRow, OddsData


session = Session()


def get_eventrow_url(row_id):
    row = select(EventRow).where(EventRow.id == row_id)
    return session.scalar(row).event_url


def add_event_data(**kwargs):
    event = OddsData(
        date=kwargs['date'],
        team_1=kwargs['team_1'],
        team_2=kwargs['team_2'],
        fin_res=kwargs['fin_res'],
        ha_ts=kwargs['ha_ts'],
        t1_ha_open=kwargs['t1_ha_open'],
        t2_ha_open=kwargs['t2_ha_open'],
        t1_ha_clos=kwargs['t1_ha_clos'],
        t2_ha_clos=kwargs['t2_ha_clos'],
        handicap_ts=kwargs['handicap_ts'],
        t1_handicap_open=kwargs['t1_handicap_open'],
        t2_handicap_open=kwargs['t2_handicap_open'],
        t1_handicap_clos=kwargs['t1_handicap_clos'],
        t2_handicap_clos=kwargs['t2_handicap_clos']
    )
    session.add(event)
