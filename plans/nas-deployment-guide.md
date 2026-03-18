# Hopper Shopper – Synology NAS Deployment Guide

## Prerequisites

- Synology NAS with **DSM 7.x** and **Container Manager** (Docker) installed
- SSH access enabled on the NAS (Control Panel → Terminal & SNMP → Enable SSH)
- A Synology DDNS hostname configured: `hopper.udidagan.synology.me`
- A valid SSL certificate for the hostname (DSM → Security → Certificate)

---

## Step 1: Push Images to Docker Hub

This happens automatically via GitHub Actions when you push to `main`. But for the first time, you can also build and push manually from your Mac:

```bash
# Log in to Docker Hub
docker login -u udidg

# Build and push backend
docker build -t udidg/hopper-shopper-backend:latest -f backend/Dockerfile.prod ./backend
docker push udidg/hopper-shopper-backend:latest

# Build and push frontend
docker build -t udidg/hopper-shopper-frontend:latest -f frontend/Dockerfile ./frontend
docker push udidg/hopper-shopper-frontend:latest
```

---

## Step 2: Prepare the NAS

### 2a. SSH into your NAS

```bash
ssh your_username@your_nas_ip
```

### 2b. Create the project directory

```bash
sudo mkdir -p /volume1/docker/hopper-shopper/nginx
```

### 2c. Copy files to the NAS

From your Mac (not inside SSH), copy the required files:

```bash
# Copy docker-compose.prod.yml
scp docker-compose.prod.yml your_username@your_nas_ip:/volume1/docker/hopper-shopper/

# Copy nginx production config
scp nginx/nginx.prod.conf your_username@your_nas_ip:/volume1/docker/hopper-shopper/nginx/

# Copy the env example as a starting point
scp .env.production.example your_username@your_nas_ip:/volume1/docker/hopper-shopper/.env
```

### 2d. Edit the `.env` file on the NAS

SSH back into the NAS and edit the environment file:

```bash
ssh your_username@your_nas_ip
cd /volume1/docker/hopper-shopper
sudo vi .env
```

Fill in the real values:

| Variable | What to set |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `POSTGRES_PASSWORD` | A strong random password |
| `DATABASE_URL` | Update the password to match `POSTGRES_PASSWORD` |
| `SECRET_KEY` | A random string (use `openssl rand -hex 32` to generate) |
| `CORS_ORIGINS` | `https://hopper.udidagan.synology.me` |
| `DOMAIN` | `hopper.udidagan.synology.me` |

---

## Step 3: Start the Stack

```bash
cd /volume1/docker/hopper-shopper
sudo docker compose -f docker-compose.prod.yml up -d
```

Verify all containers are running:

```bash
sudo docker compose -f docker-compose.prod.yml ps
```

You should see 4 containers: `nginx`, `backend`, `frontend`, `db` — all with status `Up`.

Check logs if something is wrong:

```bash
sudo docker compose -f docker-compose.prod.yml logs -f
```

---

## Step 4: Run Database Migrations

The first time you deploy, you need to run Alembic migrations:

```bash
sudo docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Step 5: Configure Synology Reverse Proxy

### 5a. Open DSM in your browser

Go to `https://your_nas_ip:5001`

### 5b. Navigate to Reverse Proxy settings

**Control Panel → Login Portal → Advanced tab → Reverse Proxy**

### 5c. Create a new rule

Click **Create** and fill in:

| Field | Value |
|-------|-------|
| **Description** | Hopper Shopper |
| **Source** | |
| Protocol | HTTPS |
| Hostname | hopper.udidagan.synology.me |
| Port | 443 |
| **Destination** | |
| Protocol | HTTP |
| Hostname | localhost |
| Port | 8080 |

### 5d. Enable WebSocket support

In the same rule, go to the **Custom Header** tab and click **Create → WebSocket**. This automatically adds the required headers for WebSocket connections.

### 5e. Save the rule

Click **Save**.

---

## Step 6: Configure SSL Certificate

### 6a. Get a certificate (if you don't have one)

Go to **Control Panel → Security → Certificate → Add**

Choose **"Get a certificate from Let's Encrypt"**:
- Domain name: `hopper.udidagan.synology.me`
- Email: your email

### 6b. Assign the certificate to the reverse proxy

Go to **Control Panel → Security → Certificate → Settings**

Find the `hopper.udidagan.synology.me` entry and assign your certificate to it.

---

## Step 7: Test the Deployment

Open your browser and navigate to:

```
https://hopper.udidagan.synology.me
```

You should see the Hopper Shopper frontend. Test the following:
- [ ] Frontend loads correctly
- [ ] Login via Telegram works
- [ ] API calls work (create a list, add items)
- [ ] WebSocket real-time updates work

---

## Updating the Application

### Automatic (via GitHub Actions)

Every push to `main` builds and pushes new images to Docker Hub. To deploy the update on your NAS:

```bash
ssh your_username@your_nas_ip
cd /volume1/docker/hopper-shopper
sudo docker compose -f docker-compose.prod.yml pull
sudo docker compose -f docker-compose.prod.yml up -d
```

### Manual

```bash
# On your Mac – build and push
docker build -t udidg/hopper-shopper-backend:latest -f backend/Dockerfile.prod ./backend
docker build -t udidg/hopper-shopper-frontend:latest -f frontend/Dockerfile ./frontend
docker push udidg/hopper-shopper-backend:latest
docker push udidg/hopper-shopper-frontend:latest

# On the NAS – pull and restart
ssh your_username@your_nas_ip
cd /volume1/docker/hopper-shopper
sudo docker compose -f docker-compose.prod.yml pull
sudo docker compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Containers won't start
```bash
sudo docker compose -f docker-compose.prod.yml logs backend
sudo docker compose -f docker-compose.prod.yml logs frontend
sudo docker compose -f docker-compose.prod.yml logs db
```

### Database connection issues
Make sure `DATABASE_URL` in `.env` matches `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

### WebSocket not connecting
Ensure you added the WebSocket custom header in the Synology reverse proxy rule (Step 5d).

### 502 Bad Gateway
The containers might still be starting. Wait 30 seconds and try again. Check that port 8080 is not used by another service:
```bash
sudo netstat -tlnp | grep 8080
```

### Reset everything
```bash
cd /volume1/docker/hopper-shopper
sudo docker compose -f docker-compose.prod.yml down -v  # WARNING: -v deletes database data
sudo docker compose -f docker-compose.prod.yml up -d
```
