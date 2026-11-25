"""
FastAPI 실행 진입점입니다.
실제 앱 구현은 app/main.py에 있습니다.
"""

from app.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)