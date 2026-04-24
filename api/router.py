from fastapi import APIRouter

from Screenshot_To_All_Formats.api.settings import router as settings_router
from Screenshot_To_All_Formats.api.conversion import router as conversion_router
from Screenshot_To_All_Formats.api.upload import router as upload_router

api_router = APIRouter()

api_router.include_router(settings_router)
api_router.include_router(conversion_router)
api_router.include_router(upload_router)
