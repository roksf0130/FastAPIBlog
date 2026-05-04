from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# aiosqlite : 비동기 환경에서 SQLite 를 사용하기 위한 비동기용 드라이버
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

# 비동기 방식으로 DB 를 이용하므로 create_engine 이 아닌 create_async_engine 을 사용
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

"""
비동기 환경에서 DB와 통신하기 위해 async_sessionmaker로 비동기 세션 팩토리를 생성
* expire_on_commit
- True
    commit이 일어나면 파이썬이 들고 있던 객체의 내용을 모두 비워버린다.
    따라서 다시 쓰려면 DB에서 새로 읽어와야 한다.
- False
    비동기 환경에서는 데이터를 다시 읽어오는 과정이 자동으로 일어나기 어렵다.
    commit 후에도 객체에 데이터가 남아 있어야 추가적인 await 호출 없이 바로 데이터를 사용할 수 있다.
"""
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 테이블을 만들기 위한 공통기능을 가진 기준 클래스 선언
class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
