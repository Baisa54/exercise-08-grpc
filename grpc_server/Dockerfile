FROM python:3.11-slim

WORKDIR /app

COPY grpc_server/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ proto/
COPY grpc_server/ grpc_server/

RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/node_registry.proto

ENV PYTHONPATH=/app
EXPOSE 50051

CMD ["python", "grpc_server/server.py"]