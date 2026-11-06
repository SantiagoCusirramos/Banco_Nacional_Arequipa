FROM python:3.11-slim
WORKDIR /app
COPY    requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY CUENTAS ./CUENTAS
EXPOSE 8001
CMD ["uvicorn", "CUENTAS.main:app", "--host", "0.0.0.0", "--port", "8001"]