from datetime import datetime

from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from pathlib import Path


class Base(DeclarativeBase):
    pass


DB_PATH = Path(__file__).parent / "weather_stylist.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

class UserORM(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(
        Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    thermo_profile: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    warmth_shift: Mapped[float] = mapped_column(
        Float, nullable=False, default=0)
    feedback_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    cold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FeedbackORM(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.tg_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temp_min: Mapped[float] = mapped_column(Float, nullable=False)
    temp_max: Mapped[float] = mapped_column(Float, nullable=False)
    wind_max: Mapped[float] = mapped_column(Float, nullable=False)
    will_rain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    thermo_profile: Mapped[int] = mapped_column(Integer, nullable=False)
    outfit_code: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[int] = mapped_column(Integer, nullable=False)


Base.metadata.create_all(bind=engine)
