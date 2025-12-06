from ..models import User, FeedbackRecord
from abc import ABC, abstractmethod


class UserRepo(ABC):
    @abstractmethod
    def get_user_by_tg_id(self, tg_id: int) -> User | None:
        '''Find user by their telegram id'''
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> User:
        """Create/save user data"""
        raise NotImplementedError


class FeedbackRepo(ABC):
    @abstractmethod
    def get_by_user_tg_id(self, user_tg_id: int) -> list[FeedbackRecord]:
        """Get all feedback records for given user"""
        raise NotImplementedError

    @abstractmethod
    def save(self, record: FeedbackRecord) -> FeedbackRecord:
        """Create/save feedback record"""
        raise NotImplementedError
