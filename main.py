from fastapi import FastAPI
from routes import router

main = FastAPI()
main.include_router(router)