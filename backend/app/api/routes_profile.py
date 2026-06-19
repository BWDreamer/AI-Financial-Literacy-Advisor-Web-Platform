from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_profile():
    return {"module": "profile", "status": "ok"}
