"""GET /seats — live seat status for the frontend grid."""
from fastapi import APIRouter
from services import booking_service

router = APIRouter()


@router.get("/seats")
async def get_seats():
    return {"seats": booking_service.get_all_seats()}
