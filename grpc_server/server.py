"""
gRPC server implementation for the Node Registry service.
"""

import concurrent.futures
import logging
import os
import sys
import time
import uuid
from datetime import datetime

import grpc
from sqlalchemy.orm import Session

# Include parent directory and current directory in module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import node_registry_pb2 as pb2
import node_registry_pb2_grpc as pb2_grpc
from database import SessionLocal, NodeModel, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grpc_server")


class NodeRegistryServicer(pb2_grpc.NodeRegistryServicer):
    """gRPC servicer for NodeRegistry methods."""

    def Register(self, request, context):
        """Register a new node in PostgreSQL."""
        logger.info("Registering node: id=%s name=%s address=%s port=%d", request.id, request.name, request.address, request.port)
        db: Session = SessionLocal()
        try:
            node_id = request.id if request.id else str(uuid.uuid4())
            node_name = request.name if request.name else node_id
            node = NodeModel(
                id=node_id,
                name=node_name,
                address=request.address,
                port=request.port,
                status=request.status or "ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(node)
            db.commit()
            db.refresh(node)

            return pb2.NodeResponse(
                id=str(node.id),
                name=node.name,
                address=node.address,
                port=node.port,
                status=node.status,
                created_at=node.created_at.isoformat() if node.created_at else ""
            )
        except Exception as err:
            db.rollback()
            logger.error("Failed to register node: %s", err)
            context.abort(grpc.StatusCode.INTERNAL, str(err))
        finally:
            db.close()

    def Get(self, request, context):
        """Retrieve node information by ID or name."""
        logger.info("Fetching node: id=%s", request.id)
        db: Session = SessionLocal()
        try:
            node = db.query(NodeModel).filter(
                (NodeModel.id == request.id) | (NodeModel.name == request.id)
            ).first()
            if not node:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Node with ID or name '{request.id}' not found")
                return pb2.NodeResponse()

            return pb2.NodeResponse(
                id=str(node.id),
                name=node.name,
                address=node.address,
                port=node.port,
                status=node.status,
                created_at=node.created_at.isoformat() if node.created_at else ""
            )
        finally:
            db.close()

    def List(self, request, context):
        """Retrieve list of all registered nodes."""
        logger.info("Listing registered nodes")
        db: Session = SessionLocal()
        try:
            nodes = db.query(NodeModel).all()
            response_nodes = [
                pb2.NodeResponse(
                    id=str(n.id),
                    name=n.name,
                    address=n.address,
                    port=n.port,
                    status=n.status,
                    created_at=n.created_at.isoformat() if n.created_at else ""
                )
                for n in nodes
            ]
            return pb2.NodeList(nodes=response_nodes)
        finally:
            db.close()

    def Delete(self, request, context):
        """Delete registered node by ID or name."""
        logger.info("Deleting node: id=%s", request.id)
        db: Session = SessionLocal()
        try:
            nodes = db.query(NodeModel).filter(
                (NodeModel.id == request.id) | (NodeModel.name == request.id)
            ).all()
            if not nodes:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Node with ID or name '{request.id}' not found")
                return pb2.Empty()

            for node in nodes:
                db.delete(node)
            db.commit()
            return pb2.Empty()
        except Exception as err:
            db.rollback()
            if context.code() is None:
                context.abort(grpc.StatusCode.INTERNAL, str(err))
            raise err
        finally:
            db.close()


def serve():
    """Start gRPC server loop."""
    port = os.getenv("GRPC_PORT", "50051")

    # Retry loop to wait for database container readiness
    max_retries = 15
    for attempt in range(max_retries):
        try:
            init_db()
            logger.info("Database initialized successfully.")
            break
        except Exception as err:
            logger.warning("Database connection attempt %d/%d failed: %s", attempt + 1, max_retries, err)
            if attempt == max_retries - 1:
                raise err
            time.sleep(2)

    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_NodeRegistryServicer_to_server(NodeRegistryServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("gRPC server listening on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()