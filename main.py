import models

from contextlib import asynccontextmanager
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database import Base, engine, get_db
from routers import posts, users


# FastAPI 생애주기를 관리
# 프로그램이 실행될 때 한 번 실행할 일과 종료되기 직전 한 번 실행할 일을 모아둠
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 프로그램이 시작될 때 DB를 확인해서 models.py에 정의한 테이블이 없으면 자동으로 생성
    # engine.begin()과 await를 사용해 DB 연결을 비동기적으로 시작
    # run_sync: SQLAlchemy의 테이블 생성은 원래 동기 방식이다.
    # 비동기 엔진에서 실행하기 위해 테이블 생성할 때만 잠깐 동기방식으로 실행한다.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 프로그램이 시작되면 코드는 여기서 대기한다.
    yield
    # 프로그램이 종료될 때 DB 커넥션을 정리한다.
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# app.mount 매개변수
# 1. static 파일에 접근할 수 있는 URL 경로
# 2. static 파일 경로
# 3. 템플릿에서 참조할 수 있는 이름
app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    # 비동기 방식에서는 db.query 대신 await db.execute를 사용
    result = await db.execute(
        # 동작원리
        # 1. Post를 모두 가져온다.
        # 2. 가져온 Post의 author를 모아서 두 번째 쿼리를 날린다. (select * from user where id in (1, 2, 3...))
        # 가져온 유저 정보를 각 Post 객체에 넣는다.
        # options(selectinload(models.Post.author): N+1 문제라고 불리는 성능저하를 해결하기 위한 기법
        # 비동기 환경의 공식과도 같다.
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
    )
    # db.execute 만 하면 데이터를 바로 쓸 수 없다. scalars()를 이용해 정의한 모델 객체만 뽑아낸 후 사용한다.
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


## login and register template_routes
@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


## StarletteHTTPException Handler
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request, exception: StarletteHTTPException
):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


### RequestValidationError Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exception: RequestValidationError
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
