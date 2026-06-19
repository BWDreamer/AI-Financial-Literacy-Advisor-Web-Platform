from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_rules():
    return {"module": "rules", "status": "ok"}
