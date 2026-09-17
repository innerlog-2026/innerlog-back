from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import auth, application, speech, retrospect
from app.core.exceptions import InnerLogException

app = FastAPI(
    title="InnerLog API",
    description="이너로그(InnerLog) API 문서",
    version="1.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://innerlog-fe.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(InnerLogException)
async def innerlog_exception_handler(request, exc: InnerLogException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)

for router in [auth.router, application.router, speech.router, retrospect.router]:
    app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Hello!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)