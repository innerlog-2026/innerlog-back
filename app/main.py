# app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="InnerLog API",
    description="이너로그(InnerLog) API 문서",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Hello!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)