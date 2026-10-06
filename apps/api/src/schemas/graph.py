import enum
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeType(str, enum.Enum):
    SERVICE = "SERVICE"
    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    ENUM = "ENUM"
    TYPE = "TYPE"
    MODULE = "MODULE"
    EXTERNAL_PACKAGE = "EXTERNAL_PACKAGE"


class GraphEdgeType(str, enum.Enum):
    DEFINES = "DEFINES"
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    snapshot_id: uuid.UUID | None = None
    total_nodes: int = 0
    total_edges: int = 0

    model_config = ConfigDict(from_attributes=True)
