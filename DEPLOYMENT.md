# CarbonLens Deployment Guide

This guide provides step-by-step instructions for deploying the CarbonLens platform. We recommend hosting the **Backend on Render** (due to Python/OCR requirements) and the **Frontend on Vercel** (for optimized React delivery).

---

## 1. Backend Deployment (Render)

Render is ideal for the FastAPI backend because it supports Docker, which we use to ensure Tesseract OCR is installed correctly.

### Step 1: Create a Dockerfile
Ensure there is a `Dockerfile` in the `backend/` directory. (One has been created for you).

### Step 2: Deploy to Render
1. Sign in to [Render](https://render.com).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub/GitLab repository.
4. Configure the service:
   - **Name**: `carbonlens-backend`
   - **Root Directory**: `backend` (Important!)
   - **Language**: `Docker`
5. Click **Advanced** to add **Environment Variables**:
   - `GROQ_API_KEY`: Your API key from [console.groq.com](https://console.groq.com/)
   - `CORS_ORIGINS`: `https://your-frontend-url.vercel.app` (Set this after deploying frontend)
   - `PYTHONUNBUFFERED`: `1`

### Step 3: Verify
Once deployed, Render will provide a URL like `https://carbonlens-backend.onrender.com`. Visit `https://carbonlens-backend.onrender.com/` to see the "running" status.

---

## 2. Frontend Deployment (Vercel)

Vercel is the best platform for Vite/React applications.

### Step 1: Deploy to Vercel
1. Sign in to [Vercel](https://vercel.com).
2. Click **Add New** > **Project**.
3. Import your GitHub repository.
4. Configure the project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (Important!)
5. Add **Environment Variables**:
   - `VITE_API_BASE_URL`: `https://carbonlens-backend.onrender.com` (Your Render URL)
6. Click **Deploy**.

---

## 3. Important: Why Render for Backend?

You may encounter a **Bundle Size Error** (e.g., "exceeds Lambda ephemeral storage limit") if you attempt to host the backend on Vercel. 

**Why this happens:**
- Our backend uses heavy machine learning and OCR libraries (**XGBoost, Prophet, OpenCV, Tesseract**).
- Together, these exceed Vercel's 500MB serverless function limit (reaching ~1.3 GB).
- **Render** uses Docker containers, which have much larger limits and allow us to install system tools like Tesseract OCR natively.

---

## 4. Post-Deployment: Connecting the Two
2. Update the `CORS_ORIGINS` environment variable to include your Vercel URL.
   - Example: `https://carbonlens-v1.vercel.app,http://localhost:5173`
3. Render will redeploy automatically.

---

## Troubleshooting FAQ

### "Mixed Content Error"
If your frontend is `https` but your `VITE_API_BASE_URL` is `http`, the browser will block the request. Ensure both use `https`.

### "Tesseract not found"
If you don't use the Docker method on Render, the system will fail to find the Tesseract binary. The Dockerfile included in the `backend` folder handles this installation automatically.

### "ML Models not loading"
Ensure that the `backend/ml/models/` folder contains your trained `.joblib` files when you push to GitHub. If they are ignored by `.gitignore`, the production server will fall back to heuristic (basic) calculations.
