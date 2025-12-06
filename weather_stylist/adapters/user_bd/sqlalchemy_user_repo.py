from sqlalchemy.orm import Session
from sqlalchemy import select

from .bd import UserORM, FeedbackORM
from weather_stylist.infra.ports import UserRepo, FeedbackRepo
from weather_stylist.models import User, FeedbackRecord


class SqlAlchemyUserRepo(UserRepo):
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_tg_id(self, tg_id: int) -> User | None:
        orm_user: UserORM | None = self.session.execute(
            select(UserORM).where(UserORM.tg_id == tg_id)).scalar_one_or_none()

        if orm_user is None:
            return None

        return User(
            tg_id=orm_user.tg_id,
            city=orm_user.city,
            name=orm_user.name,
            region=orm_user.region,
            thermo_profile=orm_user.thermo_profile,
            warmth_shift=orm_user.warmth_shift,
            feedback_count=orm_user.feedback_count,
            cold_count=orm_user.cold_count,
            hot_count=orm_user.hot_count
        )

    def get_all_users(self) -> list[User]:
        orm_users: list[UserORM] = self.session.execute(
            select(UserORM)).scalars().all()

        return [
            User(
                tg_id=orm_user.tg_id,
                city=orm_user.city,
                name=orm_user.name,
                region=orm_user.region,
                thermo_profile=orm_user.thermo_profile,
                warmth_shift=orm_user.warmth_shift,
                feedback_count=orm_user.feedback_count,
                cold_count=orm_user.cold_count,
                hot_count=orm_user.hot_count
            ) for orm_user in orm_users
        ]

    def save(self, user: User) -> User:
        orm_user: UserORM | None = self.session.get(UserORM, user.tg_id)
        if orm_user is None:
            orm_user = UserORM(
                tg_id=user.tg_id,
                city=user.city,
                name=user.name,
                region=user.region,
                thermo_profile=user.thermo_profile,
                warmth_shift=user.warmth_shift,
                feedback_count=user.feedback_count,
                cold_count=user.cold_count,
                hot_count=user.hot_count
            )

            self.session.add(orm_user)
        else:
            orm_user.tg_id = user.tg_id
            orm_user.city = user.city
            orm_user.name = user.name
            orm_user.region = user.region
            orm_user.thermo_profile = user.thermo_profile
            orm_user.warmth_shift = user.warmth_shift
            orm_user.feedback_count = user.feedback_count
            orm_user.cold_count = user.cold_count
            orm_user.hot_count = user.hot_count

        self.session.commit()
        self.session.refresh(orm_user)

        return User(
            tg_id=orm_user.tg_id,
            city=orm_user.city,
            name=orm_user.name,
            region=orm_user.region,
            thermo_profile=orm_user.thermo_profile,
            warmth_shift=orm_user.warmth_shift,
            feedback_count=orm_user.feedback_count,
            cold_count=orm_user.cold_count,
            hot_count=orm_user.hot_count,
        )


class SqlAlchemyFeedbackRepo(FeedbackRepo):
    def __init__(self, session: Session):
        self.session = session

    def save(self, record: FeedbackRecord) -> FeedbackRecord:
        orm_fb = FeedbackORM(
            user_tg_id=record.user_tg_id,
            created_at=record.created_at,
            temp_min=record.temp_min,
            temp_max=record.temp_max,
            wind_max=record.wind_max,
            will_rain=record.will_rain,
            thermo_profile=record.thermo_profile,
            outfit_code=record.outfit_code,
            label=record.label,
        )

        self.session.add(orm_fb)
        self.session.commit()
        self.session.refresh(orm_fb)

        return record

    def get_by_user_id(self, user_tg_id: int) -> list[FeedbackRecord]:
        orm_records = self.session.execute(
            select(FeedbackORM).where(FeedbackORM.user_tg_id == user_tg_id)
        ).scalars().all()

        return [
            FeedbackRecord(
                user_tg_id=fb.user_tg_id,
                created_at=fb.created_at,
                temp_min=float(fb.temp_min),
                temp_max=float(fb.temp_max),
                wind_max=float(fb.wind_max),
                will_rain=fb.will_rain,
                thermo_profile=fb.thermo_profile,
                outfit_code=fb.outfit_code,
                label=fb.label,
            )
            for fb in orm_records
        ]
