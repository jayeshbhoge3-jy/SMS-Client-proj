# SMS - Inventory & Operations Management System

A Django-based enterprise inventory, logistics, and company management web application.

---

## 🔒 Security & Environment Setup

This project uses environment variables to ensure all sensitive credentials (passwords, secret keys, API tokens) are **never** committed to Git or GitHub.

### 1. Local Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with your local database and service credentials.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start development server:
   ```bash
   python manage.py runserver
   ```

---

## 🚀 100% Free Cloud Deployment Guide

You can host this project completely free using **Render** (Web Service) + **Neon.tech** (PostgreSQL Database).

### Step 1: Create a Free PostgreSQL Database on Neon
1. Go to [Neon.tech](https://neon.tech) and sign up for a free account.
2. Create a new project (e.g., `sms-db`).
3. Under the **Dashboard**, copy your PostgreSQL connection string (`DATABASE_URL`).
   It looks like:
   ```
   postgresql://user:password@ep-xyz.region.neon.tech/neondb?sslmode=require
   ```

### Step 2: Push Your Code to GitHub
1. Create a new private or public repository on GitHub (e.g., `SMS-App`).
2. Link your local repository and push:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```
*(Note: Your `.env` file is strictly ignored by `.gitignore` and will never be pushed).*

### Step 3: Deploy on Render.com (100% Free)
1. Sign up on [Render.com](https://render.com) and link your GitHub account.
2. Click **New +** -> **Web Service**.
3. Select your GitHub repository.
4. Fill in the deployment details:
   - **Name**: `sms-app`
   - **Environment**: `Python 3`
   - **Region**: Choose the closest region (e.g., Singapore / Frankfurt / Oregon)
   - **Branch**: `main` (or `master`)
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn SMS.wsgi:application`
   - **Instance Type**: `Free`
5. In the **Environment Variables** section, add:
   - `SECRET_KEY`: *(Click Generate or enter a secure random string)*
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `*` (or your `.onrender.com` domain)
   - `DATABASE_URL`: *(Paste your Neon connection string from Step 1)*
   - `CSRF_TRUSTED_ORIGINS`: `https://your-service-name.onrender.com`
   - `EMAIL_HOST_USER`: `your-email@gmail.com`
   - `EMAIL_HOST_PASSWORD`: `your-app-password`
   - `RAZORPAY_KEY_ID`: `your-razorpay-key`
   - `RAZORPAY_KEY_SECRET`: `your-razorpay-secret`
   - `CELERY_TASK_ALWAYS_EAGER`: `True`
6. Click **Create Web Service**.
Render will automatically run `build.sh` (which installs dependencies, collects static files via WhiteNoise, and runs database migrations) and bring your site live with free HTTPS!

---

## 🛠️ Features Included for Production
- **WhiteNoise**: Automated high-performance static asset compression and caching.
- **Dynamic Database Switcher**: Uses `dj-database-url` to support cloud `DATABASE_URL` seamlessly while preserving local database support.
- **Fail-safe Celery**: Configured in eager mode for single-instance free cloud environments.
