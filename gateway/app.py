"""
FastAPI REST Gateway translating HTTP requests to gRPC calls.
"""

import logging
import os
import sys
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import grpc

# Include parent directory and current directory in module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import node_registry_pb2 as pb2
import node_registry_pb2_grpc as pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI(title="Node Registry REST Gateway", version="1.0.0")

GRPC_HOST = os.getenv("GRPC_SERVER_HOST", "grpc-server")
GRPC_PORT = os.getenv("GRPC_SERVER_PORT", "50051")


def get_grpc_stub() -> pb2_grpc.NodeRegistryStub:
    """Create and return a gRPC stub for NodeRegistry."""
    target = f"{GRPC_HOST}:{GRPC_PORT}"
    channel = grpc.insecure_channel(target)
    return pb2_grpc.NodeRegistryStub(channel)


class NodeCreate(BaseModel):
    """Pydantic model for node registration request."""
    name: str
    address: str
    port: int
    status: Optional[str] = "ACTIVE"


class NodeSchema(BaseModel):
    """Pydantic model for node response representation."""
    id: str
    name: str
    address: str
    port: int
    status: str
    created_at: str


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint required by testing harness."""
    return {"status": "ok"}


def _register_node(node_data: NodeCreate):
    stub = get_grpc_stub()
    try:
        req = pb2.RegisterRequest(
            name=node_data.name,
            address=node_data.address,
            port=node_data.port,
            status=node_data.status or "ACTIVE"
        )
        res = stub.Register(req)
        return {
            "id": res.id,
            "name": res.name,
            "address": res.address,
            "port": res.port,
            "status": res.status,
            "created_at": res.created_at
        }
    except grpc.RpcError as err:
        logger.error("gRPC error during Register: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@app.post("/nodes", response_model=NodeSchema, status_code=status.HTTP_201_CREATED)
@app.post("/api/nodes", response_model=NodeSchema, status_code=status.HTTP_201_CREATED)
def register_node(node_data: NodeCreate):
    """Register a new node via REST."""
    return _register_node(node_data)


def _list_nodes():
    stub = get_grpc_stub()
    try:
        res = stub.List(pb2.Empty())
        return [
            {
                "id": n.id,
                "name": n.name,
                "address": n.address,
                "port": n.port,
                "status": n.status,
                "created_at": n.created_at
            }
            for n in res.nodes
        ]
    except grpc.RpcError as err:
        logger.error("gRPC error during List: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@app.get("/nodes", response_model=List[NodeSchema])
@app.get("/api/nodes", response_model=List[NodeSchema])
def list_nodes():
    """List all registered nodes via REST."""
    return _list_nodes()


def _get_node(node_id: str):
    stub = get_grpc_stub()
    try:
        res = stub.Get(pb2.GetRequest(id=node_id))
        return {
            "id": res.id,
            "name": res.name,
            "address": res.address,
            "port": res.port,
            "status": res.status,
            "created_at": res.created_at
        }
    except grpc.RpcError as err:
        if err.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
        logger.error("gRPC error during Get: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@app.get("/nodes/{node_id}", response_model=NodeSchema)
@app.get("/api/nodes/{node_id}", response_model=NodeSchema)
def get_node(node_id: str):
    """Get node details by ID via REST."""
    return _get_node(node_id)


def _delete_node(node_id: str):
    stub = get_grpc_stub()
    try:
        stub.Delete(pb2.DeleteRequest(id=node_id))
        return {"message": f"Node '{node_id}' deleted successfully"}
    except grpc.RpcError as err:
        if err.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
        logger.error("gRPC error during Delete: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@app.delete("/nodes/{node_id}")
@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    """Delete a node by ID via REST."""
    return _delete_node(node_id)