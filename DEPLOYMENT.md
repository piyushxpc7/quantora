# 🚀 Quantora Deployment Guide

This guide explains how to deploy Quantora to the web for free using **Render** (Backend) and **Vercel** (Frontend).

## 1. Backend Deployment (Render)

Render is excellent for Python/FastAPI apps.

1.  **Push your code to GitHub**.
2.  **Sign up/Login to [Render](https://render.com)**.
3.  Click **"New +"** -> **"Web Service"**.
4.  Connect your GitHub repository.
5.  **Configure the Service**:
    *   **Name**: `quantora-backend`
    *   **Root Directory**: `backend`
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6.  Click **"Create Web Service"**.
7.  Wait for deployment. **Copy the URL** (e.g., `https://quantora-backend.onrender.com`).

## 2. Frontend Deployment (Vercel)

Vercel is the creators of Next.js and the best place to deploy it.

1.  **Sign up/Login to [Vercel](https://vercel.com)**.
2.  Click **"Add New..."** -> **"Project"**.
3.  Import your GitHub repository.
4.  **Configure the Project**:
    *   **Framework Preset**: Next.js (Auto-detected)
    *   **Root Directory**: `frontend` (Click "Edit" next to Root Directory and select `frontend`).
    *   **Environment Variables**:
        *   Name: `NEXT_PUBLIC_API_URL`
        *   Value: `https://quantora-backend.onrender.com` (The URL from Step 1, **without** the trailing slash).
5.  Click **"Deploy"**.

## 3. Verification

1.  Open your Vercel URL (e.g., `https://quantora.vercel.app`).
2.  Go to the **Drift Monitor** page.
3.  If the charts load and you don't see connection errors, everything is working!

## 🐳 Local Docker Deployment

If you prefer to run it locally with Docker:

```bash
docker-compose up --build
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
