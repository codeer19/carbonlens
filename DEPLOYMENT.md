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

## 3. Alternative: Vercel Multi-Service (Monorepo)

If you want to host both frontend and backend on Vercel using the same project, we have added a `vercel.json` to the root.

**Important Note:** Vercel's native Python runtime does **not** include Tesseract OCR. If you use this method, the "Camera Scan" and "Image Scan" features will rely solely on the Groq Vision fallback, which is slightly less robust than the full OCR pipeline. For the best experience, we still recommend **Render** for the backend.

### Setup for Monorepo:
1. Ensure `vercel.json` is in your root directory.
2. In Vercel, import the **Root** of your repository (not just the `frontend` folder).
3. Vercel will automatically detect the services.
4. Set `VITE_API_BASE_URL` to `/_/backend`.

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
