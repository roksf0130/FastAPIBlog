from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from config import settings


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    posts: Mapped[list[Post]] = relationship(
        # back_populates="author": Post 모델의 author와 연결하기
        # 나(Post 리스트)랑 연결된 상대방(Post 모델) 쪽에도 나를 가리키는 author라는 이름의 변수가 있을 테니 서로 연결해 줘
        # cascade="all, delete-orphan: User가 삭제되면 User가 작성한 Post도 모두 삭제
        back_populates="author",
        cascade="all, delete-orphan",
    )

    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # property 데코레이터
    # 클래스 내부 함수를 쓰려면 user.image_path()와 같이 괄호를 붙여야 한다.
    # 하지만 property 데코레이터를 사용하면 user.image_path라고만 써도 실행이 된다.
    # 클래스 내부 변수처럼 보이지만 실제로는 함수처럼 계산해서 값을 돌려주는 가짜 변수
    @property
    def image_path(self) -> str:
        if self.image_file:
            return f"https://{settings.s3_bucket_name}.s3.{settings.s3_region}.amazonaws.com/profile_pics/{self.image_file}"
        return "/static/profile_pics/default.jpg"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # realationship으로 author와 posts를 연결해도, 실제 DB수준에서 두 테이블을 연결하기 위해 ForeignKey 설정
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # lambda를 사용하지 않으면 서버가 켜진 시간이 고정된다.
        # lambda를 사용해야 데이터가 생성될 때마다 순간의 시간으로 새로 계산해서 넣어준다.
        default=lambda: datetime.now(UTC),
    )
    likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # relationship(back_populates="posts": 반대로 Post에서 User와 연결하기
    author: Mapped[User] = relationship(back_populates="posts")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship(back_populates="reset_tokens")
