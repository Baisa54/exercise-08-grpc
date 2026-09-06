FROM python:3.11-slim

WORKDIR /app

COPY gateway/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ proto/
COPY gateway/ gateway/

RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/node_registry.proto

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]