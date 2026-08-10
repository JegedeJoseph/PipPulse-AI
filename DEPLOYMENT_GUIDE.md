# PipPulse-AI Windows Deployment Guide (No Docker)

## Prerequisites
- Python 3.11+ installed
- Node.js 18+ installed
- MongoDB (local or cloud instance)
- PostgreSQL (local or cloud instance)
- PM2 for process management

## Installation Commands

### 1. Install PM2 Globally
```bash
npm install -g pm2
npm install -g pm2-windows-startup
pm2-startup install
```

### 2. Backend Setup

#### Navigate to backend directory
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
```

#### Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

#### Install dependencies
```bash
pip install -r requirements-core.txt
pip install -r requirements-ml.txt
```

#### Download spaCy model
```bash
python -m spacy download en_core_web_sm
```

#### Create environment file
```bash
copy .env.example .env
# Edit .env with your actual configuration
```

#### Create logs directory
```bash
mkdir logs
```

### 3. Frontend Setup

#### Navigate to frontend directory
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
```

#### Install dependencies
```bash
npm install
```

#### Create environment file
```bash
copy .env.local.example .env.local
# Edit .env.local with your actual configuration
```

#### Build the application
```bash
npm run build
```

#### Create logs directory
```bash
mkdir logs
```

## Deployment Commands

### 1. Start Backend with PM2
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
pm2 start ecosystem.config.js
pm2 save
```

### 2. Start Frontend with PM2
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
pm2 start ecosystem.config.js
pm2 save
```

### 3. Check PM2 Status
```bash
pm2 status
pm2 logs
```

### 4. Stop Services
```bash
pm2 stop pippulse-backend
pm2 stop pippulse-frontend
```

### 5. Restart Services
```bash
pm2 restart pippulse-backend
pm2 restart pippulse-frontend
```

### 6. Delete Services
```bash
pm2 delete pippulse-backend
pm2 delete pippulse-frontend
pm2 save
```

## Firewall Configuration

### Allow inbound connections for backend and frontend
```powershell
# Allow backend port 8000
New-NetFirewallRule -DisplayName "PipPulse Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Allow frontend port 3000
New-NetFirewallRule -DisplayName "PipPulse Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

## Database Setup

### MongoDB
- Install MongoDB locally or use MongoDB Atlas
- Update `MONGODB_URI` in backend `.env` file

### PostgreSQL
- Install PostgreSQL locally or use cloud service
- Update `POSTGRES_URI` in backend `.env` file
- Create database: `createdb pippulse`

## Testing

### Test Backend
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed
```

### Test Frontend
```bash
# Open browser
http://localhost:3000
```

## Monitoring

### View Logs
```bash
# View all logs
pm2 logs

# View specific service logs
pm2 logs pippulse-backend
pm2 logs pippulse-frontend

# View logs in real-time
pm2 logs --lines 100
```

### Monitor Performance
```bash
pm2 monit
```

## Troubleshooting

### Backend Issues
```bash
# Check if backend is running
pm2 status

# View error logs
pm2 logs pippulse-backend --err

# Restart backend
pm2 restart pippulse-backend
```

### Frontend Issues
```bash
# Check if frontend is running
pm2 status

# View error logs
pm2 logs pippulse-frontend --err

# Restart frontend
pm2 restart pippulse-frontend
```

### Database Connection Issues
- Verify MongoDB is running: `mongod --version`
- Verify PostgreSQL is running: `psql --version`
- Check connection strings in `.env` files

## Data Persistence

### TinyFlux Data Files
- Signals data: `tinyflux_signals.csv` (in backend directory)
- Price data: `tinyflux_prices.csv` (in backend directory)

### BurnerRedis Data File
- Redis data: `redis_data.dat` (in backend directory)

## Development Mode

### Run Backend in Development
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Frontend in Development
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
npm run dev
```

## Production Mode

### Production Backend Startup
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
venv\Scripts\activate
pm2 start ecosystem.config.js
pm2 save
```

### Production Frontend Startup
```bash
cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
npm run build
pm2 start ecosystem.config.js
pm2 save
```

## Quick Start Summary

```bash
# 1. Install PM2
npm install -g pm2 pm2-windows-startup
pm2-startup install

# 2. Setup Backend
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-core.txt
pip install -r requirements-ml.txt
python -m spacy download en_core_web_sm
copy .env.example .env
mkdir logs

# 3. Setup Frontend
cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
npm install
copy .env.local.example .env.local
npm run build
mkdir logs

# 4. Start Services
cd C:\Users\ayolu\Desktop\PipPulse-AI\backend
pm2 start ecosystem.config.js
pm2 save

cd C:\Users\ayolu\Desktop\PipPulse-AI\frontend
pm2 start ecosystem.config.js
pm2 save

# 5. Configure Firewall
New-NetFirewallRule -DisplayName "PipPulse Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "PipPulse Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# 6. Test
curl http://localhost:8000/health
# Open http://localhost:3000 in browser
```

## Notes

- **TinyFlux** replaces InfluxDB - data stored in CSV files
- **BurnerRedis** replaces Redis - data stored in .dat file
- Both are embedded databases requiring no external server
- PM2 manages processes and auto-restart on failure
- All data persists in files in the backend directory
