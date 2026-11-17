FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY seguridad ./seguridad

RUN mkdir -p /app/runtime

EXPOSE 8000

CMD ["uvicorn", "seguridad.app:app", "--host", "0.0.0.0", "--port", "8000"]
