from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["root"])
def root() -> dict:
    return {"message": "OpsPilot backend is running"}

