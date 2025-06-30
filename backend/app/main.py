from fastapi import FastAPI
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .database import engine
from .models import VisaReportLine

app = FastAPI()

# CORS Configuration
origins = [
    "http://localhost:3000",  # React default
    "http://127.0.0.1:3000",  # Alternative localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],     # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],     # Allows all headers
    expose_headers=["*"]     # Exposes all headers to frontend
)


@app.on_event("startup")
def on_startup():
    # Create all tables defined in models.py
    VisaReportLine.__table__.create(bind=engine, checkfirst=True)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    print(f"Received file: {file.filename}")
    contents = await file.read()
    return {"filename": file.filename}


app.include_router(router)