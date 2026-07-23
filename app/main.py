from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid
import json

app = FastAPI(title="Cloud Data Pipeline - Job Tracker & Blob Storage")

# ── Configuration ─────────────────────────────────────────────
CONN_STR = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

BLOB_CONTAINER = "job-files"
blob_service = BlobServiceClient.from_connection_string(CONN_STR)

# ── In-Memory Job Store (replace with DB in production) ─────
jobs_db = {}

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobCreate(BaseModel):
    name: str
    description: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str
    files: List[str]

# ── Startup: Ensure blob container exists ───────────────────
@app.on_event("startup")
async def startup():
    try:
        blob_service.create_container(BLOB_CONTAINER)
        print(f"✅ Created container: {BLOB_CONTAINER}")
    except Exception as e:
        print(f"ℹ️ Container already exists or other: {e}")

# ═════════════════════════════════════════════════════════════
# JOB TRACKER ENDPOINTS
# ═════════════════════════════════════════════════════════════

@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreate):
    """Create a new job."""
    job_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    jobs_db[job_id] = {
        "id": job_id,
        "name": job.name,
        "description": job.description,
        "status": JobStatus.PENDING,
        "created_at": now,
        "updated_at": now,
        "files": []
    }
    return jobs_db[job_id]

@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs():
    """List all jobs."""
    return list(jobs_db.values())

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a specific job by ID."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]

@app.patch("/jobs/{job_id}/status")
async def update_job_status(job_id: str, status: str = Form(...)):
    """Update job status."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    if status not in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Invalid status")
    jobs_db[job_id]["status"] = status
    jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
    return jobs_db[job_id]

@app.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Delete a job and its associated blobs."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Clean up blobs
    for filename in jobs_db[job_id]["files"]:
        blob_path = f"{job_id}/{filename}"
        try:
            blob_client = blob_service.get_blob_client(BLOB_CONTAINER, blob_path)
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
    
    del jobs_db[job_id]
    return {"detail": "Job deleted"}

# ═════════════════════════════════════════════════════════════
# BLOB STORAGE ENDPOINTS
# ═════════════════════════════════════════════════════════════

@app.post("/jobs/{job_id}/upload")
async def upload_file(job_id: str, file: UploadFile = File(...)):
    """Upload a file and associate it with a job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Unique blob path: job_id/filename
    blob_path = f"{job_id}/{file.filename}"
    blob_client = blob_service.get_blob_client(BLOB_CONTAINER, blob_path)
    
    # Upload
    contents = await file.read()
    blob_client.upload_blob(contents, overwrite=True)
    
    # Track in job
    if file.filename not in jobs_db[job_id]["files"]:
        jobs_db[job_id]["files"].append(file.filename)
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    return {
        "message": "File uploaded",
        "job_id": job_id,
        "filename": file.filename,
        "blob_path": blob_path,
        "size": len(contents)
    }

@app.get("/jobs/{job_id}/files/{filename}")
async def download_file(job_id: str, filename: str):
    """Download a file associated with a job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    blob_path = f"{job_id}/{filename}"
    blob_client = blob_service.get_blob_client(BLOB_CONTAINER, blob_path)
    
    try:
        downloader = blob_client.download_blob()
        return StreamingResponse(
            downloader.chunks(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in blob storage")

@app.get("/jobs/{job_id}/files")
async def list_job_files(job_id: str):
    """List all files for a job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "files": jobs_db[job_id]["files"]}

@app.delete("/jobs/{job_id}/files/{filename}")
async def delete_file(job_id: str, filename: str):
    """Delete a specific file from a job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    blob_path = f"{job_id}/{filename}"
    blob_client = blob_service.get_blob_client(BLOB_CONTAINER, blob_path)
    
    try:
        blob_client.delete_blob()
        jobs_db[job_id]["files"].remove(filename)
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
        return {"detail": "File deleted"}
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

# ═════════════════════════════════════════════════════════════
# HEALTH & ROOT
# ═════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "service": "Cloud Data Pipeline",
        "version": "1.0.0",
        "endpoints": {
            "jobs": "/jobs",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "blob_connected": True}