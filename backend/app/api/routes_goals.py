from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_goals():
    return {"module": "goals", "status": "ok"}
