"""ZEVQ Preflight application."""
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from .analyzer import analyze, read_zip, MAX_BYTES

app = FastAPI(title="ZEVQ Preflight", version="0.1.0", docs_url="/api/docs")

@app.get("/")
def index():
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")

@app.get("/health")
def health():
    return {"status":"ok"}

def archive_url(url, branch):
    p = urlparse(url)
    if p.scheme!="https" or p.hostname!="github.com" or p.port is not None or p.query or p.fragment or p.username or p.password:
        raise ValueError("Only HTTPS github.com repository URLs are supported")
    if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?",p.path):
        raise ValueError("Enter github.com/owner/repo")
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,120}",branch) or ".." in branch:
        raise ValueError("Invalid branch name")
    return "https://api.github.com/repos/"+p.path.strip("/")+"/zipball/"+branch

async def download(repo, branch):
    url = archive_url(repo, branch)
    async with httpx.AsyncClient(follow_redirects=False,timeout=25) as client:
        r = await client.get(url)
        if r.status_code in (301,302,303,307,308):
            target = r.headers.get("location","")
            parsed = urlparse(target)
            if parsed.scheme!="https" or parsed.hostname!="codeload.github.com":
                raise ValueError("Unexpected archive redirect")
            r = await client.get(target)
        if r.status_code!=200: raise ValueError(f"GitHub download failed (HTTP {r.status_code})")
        if len(r.content)>MAX_BYTES: raise ValueError("Repository archive is too large")
        return read_zip(r.content)

@app.post("/api/scan/github")
async def github_scan(repo_url:str=Form(...), branch:str=Form("main"), baseline_branch:str=Form("")):
    try:
        files = await download(repo_url,branch)
        baseline = await download(repo_url,baseline_branch) if baseline_branch.strip() else None
        return analyze(files,baseline)
    except (ValueError,httpx.HTTPError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/api/scan/zip")
async def zip_scan(file:UploadFile=File(...)):
    try:
        return analyze(read_zip(await file.read(MAX_BYTES+1)))
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e
