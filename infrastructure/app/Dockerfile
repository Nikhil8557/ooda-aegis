FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY seed_db.py .
RUN mkdir -p data && python seed_db.py data/customers.db
COPY public_docs ./public_docs
COPY fake_secrets.env ./.env
COPY tests ./tests
COPY service ./service
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
