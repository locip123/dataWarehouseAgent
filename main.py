from fastapi import FastAPI

from app.router.query_router import router as query_router


app = FastAPI()
app.include_router(query_router)
