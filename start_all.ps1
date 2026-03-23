Write-Host "Starting all components of CausalMedFusion..."

# 1. Redis
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Redis; .\redis-server.exe" -WindowStyle Normal

# 2. Django Backend
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Backend; .\venv\Scripts\python.exe manage.py runserver" -WindowStyle Normal

# 3. Celery Worker
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Backend; .\venv\Scripts\python.exe -m celery -A config worker -Q image_queue,report_queue,labs_queue,vitals_queue,embedding_queue,celery -l info --pool=solo" -WindowStyle Normal

# 4. Core Processing Gateway (CPU Bound)
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Microservices; ..\Backend\venv\Scripts\python.exe -m uvicorn core_gateway.main:app --host 0.0.0.0 --port 8001" -WindowStyle Normal

# 5. ML Engine Gateway (GPU Bound - loads PyTorch lazily)
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Microservices; ..\Backend\venv\Scripts\python.exe -m uvicorn ml_gateway.main:app --host 0.0.0.0 --port 8005" -WindowStyle Normal

# 6. React Frontend
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "cd Frontend\causalmedfusion-app; npm run dev" -WindowStyle Normal

Write-Host "All components started in separate windows."
