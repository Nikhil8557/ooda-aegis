FROM python:3.12-slim
WORKDIR /agent
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY aegis ./aegis
ENV PYTHONUNBUFFERED=1
EXPOSE 8090
CMD ["uvicorn", "aegis.server:api", "--host", "0.0.0.0", "--port", "8090"]
