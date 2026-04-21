import os
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.database import get_db, init_db, async_session
from app.models import Request as PqrsRequest, Comment, User
from app.auth import verify_password, create_token, decode_token, hash_password, auth_check
from app.seed import seed_database
from app.agent import classify_request, auto_respond, escalate_case, summarize_case
from app.i18n import get_t

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_lang(request: Request) -> str:
    return request.cookies.get("pf_lang", "en")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as db:
        await seed_database(db)
    yield


app = FastAPI(title="Projects Factory PQRS", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard" if auth_check(request) else "/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth_check(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    lang = get_lang(request)
    return templates.TemplateResponse("login.html", {"request": request, "t": get_t(lang), "lang": lang})


@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    lang = get_lang(request)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, "t": get_t(lang), "lang": lang,
            "error": "Invalid credentials" if lang == "en" else "Credenciales incorrectas"
        })
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("access_token", create_token(email), httponly=True, max_age=3600 * 8)
    return response


@app.get("/logout")
async def logout():
    r = RedirectResponse(url="/login", status_code=302)
    r.delete_cookie("access_token")
    return r


@app.get("/lang/{lang}")
async def set_lang(lang: str, request: Request):
    r = RedirectResponse(url=request.headers.get("referer", "/dashboard"), status_code=302)
    r.set_cookie("pf_lang", lang if lang in ("en", "es") else "en")
    return r


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    all_reqs = (await db.execute(select(PqrsRequest).order_by(PqrsRequest.created_at.desc()))).scalars().all()

    total = len(all_reqs)
    open_count = sum(1 for r in all_reqs if r.status == "open")
    resolved_count = sum(1 for r in all_reqs if r.status in ("resolved", "closed"))
    escalated_count = sum(1 for r in all_reqs if r.is_escalated)

    resolved_reqs = [r for r in all_reqs if r.resolved_at and r.created_at]
    avg_hours = 0
    if resolved_reqs:
        total_h = sum((r.resolved_at - r.created_at).total_seconds() / 3600 for r in resolved_reqs)
        avg_hours = round(total_h / len(resolved_reqs), 1)

    type_counts = {t: sum(1 for r in all_reqs if r.type == t) for t in ["petition", "complaint", "claim", "suggestion"]}
    status_counts = {s: sum(1 for r in all_reqs if r.status == s) for s in ["open", "in_progress", "resolved", "closed", "escalated"]}

    recent = all_reqs[:8]
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "total": total, "open_count": open_count, "resolved_count": resolved_count,
        "escalated_count": escalated_count, "avg_hours": avg_hours,
        "type_counts": type_counts, "status_counts": status_counts,
        "recent_requests": recent,
    })


@app.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request, type: str = None, status: str = None, search: str = None, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    q = select(PqrsRequest).order_by(PqrsRequest.created_at.desc())
    if type:
        q = q.where(PqrsRequest.type == type)
    if status:
        q = q.where(PqrsRequest.status == status)
    if search:
        q = q.where(
            PqrsRequest.subject.ilike(f"%{search}%") |
            PqrsRequest.customer_name.ilike(f"%{search}%") |
            PqrsRequest.ticket_id.ilike(f"%{search}%")
        )
    reqs = (await db.execute(q)).scalars().all()
    return templates.TemplateResponse("requests.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "requests": reqs, "filter_type": type or "", "filter_status": status or "", "search": search or "",
        "now": datetime.utcnow(),
    })


@app.get("/requests/{req_id}", response_class=HTMLResponse)
async def request_detail(request: Request, req_id: int, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        return RedirectResponse(url="/login", status_code=302)
    lang = get_lang(request)
    pqrs = (await db.execute(select(PqrsRequest).where(PqrsRequest.id == req_id))).scalar_one_or_none()
    if not pqrs:
        raise HTTPException(status_code=404)
    comments = (await db.execute(
        select(Comment).where(Comment.request_id == req_id).order_by(Comment.created_at)
    )).scalars().all()
    return templates.TemplateResponse("request_detail.html", {
        "request": request, "t": get_t(lang), "lang": lang,
        "pqrs": pqrs, "comments": comments, "now": datetime.utcnow(),
    })


@app.post("/requests/{req_id}/comment")
async def add_comment(req_id: int, request: Request, body: str = Form(...), is_internal: bool = Form(False), db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    comment = Comment(request_id=req_id, author="Demo User", body=body, is_internal=is_internal)
    db.add(comment)
    await db.commit()
    return RedirectResponse(url=f"/requests/{req_id}", status_code=302)


@app.post("/api/agent/classify/{req_id}")
async def api_classify(req_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    pqrs = (await db.execute(select(PqrsRequest).where(PqrsRequest.id == req_id))).scalar_one_or_none()
    if not pqrs:
        raise HTTPException(status_code=404)
    result = await classify_request(pqrs, get_lang(request))
    return JSONResponse({"result": result})


@app.post("/api/agent/respond/{req_id}")
async def api_respond(req_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    pqrs = (await db.execute(select(PqrsRequest).where(PqrsRequest.id == req_id))).scalar_one_or_none()
    if not pqrs:
        raise HTTPException(status_code=404)
    result = await auto_respond(pqrs, get_lang(request))
    return JSONResponse({"result": result})


@app.post("/api/agent/escalate/{req_id}")
async def api_escalate(req_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    pqrs = (await db.execute(select(PqrsRequest).where(PqrsRequest.id == req_id))).scalar_one_or_none()
    if not pqrs:
        raise HTTPException(status_code=404)
    result = await escalate_case(pqrs, get_lang(request))
    return JSONResponse({"result": result})


@app.post("/api/agent/summarize/{req_id}")
async def api_summarize(req_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not auth_check(request):
        raise HTTPException(status_code=401)
    pqrs = (await db.execute(select(PqrsRequest).where(PqrsRequest.id == req_id))).scalar_one_or_none()
    if not pqrs:
        raise HTTPException(status_code=404)
    comments = (await db.execute(select(Comment).where(Comment.request_id == req_id))).scalars().all()
    result = await summarize_case(pqrs, list(comments), get_lang(request))
    return JSONResponse({"result": result})
