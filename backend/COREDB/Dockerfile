FROM python:3.11-slim
WORKDIR /app
COPY requirements-coredb.txt .
RUN pip install -r requirements-coredb.txt
COPY COREDB ./COREDB

EXPOSE 8012
CMD ["uvicorn", "COREDB.main:app", "--host", "0.0.0.0", "--port", "8012"]
