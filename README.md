# ☁️ Cloud Data Pipeline

&gt; FastAPI job-tracking service with Azure Blob Storage integration — a cloud-native portfolio project.

## 🚀 What It Does

- **Job Tracker**: Create, track status, and manage data processing jobs
- **Blob Storage**: Upload, download, and organize files per job via Azure Blob Storage
- **Local Dev**: Full Docker setup with Azurite (Azure Storage Emulator) — no cloud costs

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI |
| Blob Storage | Azure Blob Storage (Azurite emulator) |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/lonyoriconsulting-maker/cloud-data-pipeline.git
cd cloud-data-pipeline

# Run
docker compose up --build

# Test
curl http://localhost:8000/health

## 📡 API Endpoints

| Endpoint                  | Method | Description        |
| ------------------------- | ------ | ------------------ |
| `/jobs`                   | POST   | Create a new job   |
| `/jobs`                   | GET    | List all jobs      |
| `/jobs/{id}`              | GET    | Get job details    |
| `/jobs/{id}/status`       | PATCH  | Update job status  |
| `/jobs/{id}/upload`       | POST   | Upload file to job |
| `/jobs/{id}/files`        | GET    | List job files     |
| `/jobs/{id}/files/{name}` | GET    | Download file      |
| `/docs`                   | GET    | Swagger UI         |

## 🏗️ Architecture

┌─────────────┐     HTTP      ┌─────────────┐     Blob API     ┌─────────────┐
│   Client    │ ─────────────→│  FastAPI    │ ───────────────→│   Azurite   │
│  (curl/     │               │   Service   │                  │  (Emulator) │
│   browser)  │ ←─────────────│   :8000     │ ←───────────────│   :10000    │
└─────────────┘               └─────────────┘                  └─────────────┘

## 📁 Blob Organization

job-files/
├── 095b0b32/
│   └── test-data.csv
├── a1b2c3d4/
│   └── report.pdf

## 🧪 Verified With

✅ curl API testing
✅ Azure Storage Explorer (local emulator connection)
✅ Docker Compose health checks

## 🗺️ Roadmap

[x] FastAPI + Azurite integration
[ ] PostgreSQL persistence layer
[ ] Async background jobs (Celery + Redis)
[ ] Deploy to Azure Container Apps
[ ] CI/CD with GitHub Actions

## 📸 Screenshot

![Azure Storage Explorer showing uploaded blobs]assets/storage-explorer.png

---

**Built by [lonyoriconsulting-maker](https://github.com/lonyoriconsulting-maker)
