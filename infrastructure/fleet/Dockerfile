FROM python:3.12-slim
RUN pip install --no-cache-dir redis==5.2.1
COPY node.py /node.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "/node.py"]
