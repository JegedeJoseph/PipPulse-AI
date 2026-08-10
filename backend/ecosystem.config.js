module.exports = {
  apps: [{
    name: 'pippulse-backend',
    script: 'venv\\Scripts\\python.exe',
    args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
    cwd: 'C:\\Users\\ayolu\\Desktop\\PipPulse-AI\\backend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      PYTHONUNBUFFERED: '1',
      ENVIRONMENT: 'production'
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true
  }]
};
