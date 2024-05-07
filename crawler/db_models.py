from .db import Model
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EventRow(Model):
    __tablename__ = 'event_rows'

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(8), index=True)
    event_url: Mapped[str] = mapped_column(unique=True)

    odds_data: Mapped["OddsData"] = relationship(back_populates="eventrow")

    def __repr__(self):
        return f"EventRow({self.id}, {self.event_id}, {self.event_url})"


class OddsData(Model):
    __tablename__ = 'odds_datas'

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str]
    team_1: Mapped[str]
    team_2: Mapped[str]
    fin_res: Mapped[str]
    # home/away opening ts
    ha_ts: Mapped[str]
    # team 1 opening home/away
    t1_ha_open: Mapped[float]
    # team 2 opening home/away
    t2_ha_open: Mapped[float]
    # team 1 closing home/away
    t1_ha_clos: Mapped[float]
    # team 2 closing home/away
    t2_ha_clos: Mapped[float]
    # asian handicap
    handicap_ts: Mapped[str]
    t1_handicap_open: Mapped[float]
    t2_handicap_open: Mapped[float]
    t1_handicap_clos: Mapped[float]
    t2_handicap_clos: Mapped[float]

    event_id: Mapped[int] = mapped_column(ForeignKey("event_rows.id"))
    event_row: Mapped["EventRow"] = relationship(back_populates="oddsdata")

    def __repr__(self) -> str:
        return (f"OddsData(date: {self.date}\n"
                f"{self.team_1} - {self.fin_res} - {self.team_2}\n"
                f"\thome/away opening timestamp: {self.ha_ts}\n"
                f"team 1 home/away opening: {self.t1_ha_open}\n"
                f"team 2 opening home/away: {self.t2_ha_open}\n"
                f"team 1 closing home/away: {self.t1_ha_clos}\n"
                f"team 2 closing home/away: {self.t2_ha_clos}\n"
                f"\tasian handicap timastamp: {self.handicap_ts}\n"
                f"Team 1 Opening Asian Handicap: {self.t1_handicap_open}"
                f"Team 2 Opening Asian Handicap: {self.t2_handicap_open}"
                f"Team 1 Closing Asian Handicap: {self.t1_handicap_clos}"
                f"Team 2 Closing Asian Handicap: {self.t2_handicap_clos})")
