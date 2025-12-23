from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .bd import UserORM, FeedbackORM
from ...infra import UserRepo, FeedbackRepo
from ...models import User, FeedbackRecord

def user_from_orm(orm: UserORM) -> User:
    return User(
        tg_id=orm.tg_id,
        city=orm.city,
        name=orm.name,
        region=orm.region,
        thermo_profile=orm.thermo_profile,
        warmth_shift=orm.warmth_shift,
        feedback_count=orm.feedback_count,
        cold_count=orm.cold_count,
        hot_count=orm.hot_count,
    )


def feedback_from_orm(fb: FeedbackORM) -> FeedbackRecord:
    return FeedbackRecord(
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
    
def feedback_orm_from_record(record: FeedbackRecord) -> FeedbackORM:
    return FeedbackORM(
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

class SqlAlchemyUserRepo(UserRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_tg_id(self, tg_id: int) -> User | None:
        result = await self.session.execute(
            select(UserORM).where(UserORM.tg_id == tg_id)
        )
        orm_user: UserORM | None = result.scalar_one_or_none()

        if orm_user is None:
            return None

        return user_from_orm(orm_user)

    async def get_all_users(self) -> list[User]:
        result = await self.session.execute(select(UserORM))
        orm_users: list[UserORM] = list(result.scalars().all())

        return [
            user_from_orm(orm_user) for orm_user in orm_users
        ]

    async def save(self, user: User) -> User:
        orm_user: UserORM | None = await self.session.get(UserORM, user.tg_id)

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

        await self.session.commit()
        await self.session.refresh(orm_user)

        return user_from_orm(orm_user)


class SqlAlchemyFeedbackRepo(FeedbackRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, record: FeedbackRecord) -> FeedbackRecord:
        orm_fb = feedback_orm_from_record(record)

        self.session.add(orm_fb)
        await self.session.commit()
        await self.session.refresh(orm_fb)

        return record

    async def get_by_user_id(self, user_tg_id: int) -> list[FeedbackRecord]:
        result = await self.session.execute(select(FeedbackORM).where(FeedbackORM.user_tg_id == user_tg_id))
        orm_records = result.scalars().all()

        return [
            feedback_from_orm(orm_record) for orm_record in orm_records
        ]
