"""Import/Export routes — split into importers and exporters sub-routers."""

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}", tags=["Import/Export"])

from app.routers.import_export.import_routes import import_router
from app.routers.import_export.export_routes import export_router

router.include_router(import_router)
router.include_router(export_router)
