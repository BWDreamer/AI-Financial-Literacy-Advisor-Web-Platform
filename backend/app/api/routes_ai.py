from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_ai():
    return {"module": "ai", "status": "ok"}
