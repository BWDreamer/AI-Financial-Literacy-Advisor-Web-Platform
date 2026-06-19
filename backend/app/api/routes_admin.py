from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_admin():
    return {"module": "admin", "status": "ok"}
