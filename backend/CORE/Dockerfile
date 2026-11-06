#dockerfile para el backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY CORE ./CORE

EXPOSE 8000

# Ahora le decimos a Uvicorn que busque main dentro de CORE
CMD ["uvicorn", "CORE.main:app", "--host", "0.0.0.0", "--port", "8000"]