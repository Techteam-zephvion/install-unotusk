import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.repository import Repository
from apps.api.src.models.service import Service
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.graph import (
    GraphEdge,
    GraphEdgeType,
    GraphNode,
    GraphNodeType,
    GraphResponse,
)
from apps.api.src.services.repository_service import RepositoryService


class GraphService:
    @staticmethod
    async def get_project_graph(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> GraphResponse:
        """Construct the code knowledge graph for the project's latest snapshot.

        Retrieves files, symbols, and dependencies scoped strictly to the active
        RepositorySnapshot. Deduplicates nodes and edges, preserving symbol hierarchy
        and external package dependencies.
        """
        # 1. Verify project authorization (preserves multi-tenant isolation)
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        # 2. Retrieve services for this project
        services_query = (
            select(Service)
            .where(Service.project_id == project.id)
            .order_by(Service.name.asc())
        )
        services_res = await session.execute(services_query)
        services = services_res.scalars().all()

        # 3. Resolve the latest RepositorySnapshot
        snapshot = await RepositoryService._get_latest_snapshot(session, project.id)

        nodes: dict[str, GraphNode] = {}
        edges: dict[tuple[str, str, GraphEdgeType], GraphEdge] = {}

        # 4. Build service nodes
        service_slug_map = {s.slug: str(s.id) for s in services}
        for s in services:
            s_id = str(s.id)
            nodes[s_id] = GraphNode(
                id=s_id,
                type=GraphNodeType.SERVICE,
                label=s.name,
                metadata={
                    "name": s.name,
                    "slug": s.slug,
                    "tier": s.tier,
                    "description": s.description,
                    **(s.service_metadata or {}),
                },
            )

        # 5. Build service-to-service dependency edges (if specified in metadata)
        for s in services:
            deps = (s.service_metadata or {}).get("depends_on")
            if isinstance(deps, list):
                for dep in deps:
                    target_id = None
                    if dep in service_slug_map:
                        target_id = service_slug_map[dep]
                    elif str(dep) in nodes:
                        target_id = str(dep)
                    if target_id and target_id != str(s.id):
                        edge_key = (str(s.id), target_id, GraphEdgeType.DEPENDS_ON)
                        edges[edge_key] = GraphEdge(
                            id=f"{s.id}->{target_id}:{GraphEdgeType.DEPENDS_ON.value}",
                            source=str(s.id),
                            target=target_id,
                            type=GraphEdgeType.DEPENDS_ON,
                        )

        if snapshot is None:
            node_list = list(nodes.values())
            edge_list = list(edges.values())
            return GraphResponse(
                nodes=node_list,
                edges=edge_list,
                snapshot_id=None,
                total_nodes=len(node_list),
                total_edges=len(edge_list),
            )

        # 6. Retrieve files strictly for the latest snapshot (bulk query)
        files_query = (
            select(RepositoryFile)
            .where(RepositoryFile.snapshot_id == snapshot.id)
            .order_by(RepositoryFile.path.asc())
        )
        files_res = await session.execute(files_query)
        files = files_res.scalars().all()
        file_map: dict[uuid.UUID, RepositoryFile] = {f.id: f for f in files}

        if not files and not services:
            return GraphResponse(
                nodes=[],
                edges=[],
                snapshot_id=snapshot.id,
                total_nodes=0,
                total_edges=0,
            )

        # 7. Retrieve active repository for this snapshot
        repo_query = select(Repository).where(Repository.id == snapshot.repository_id)
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalar_one_or_none()

        repo_node_id = None
        if repo is not None and repo.service_id is not None:
            s_id = str(repo.service_id)
            if s_id in nodes:
                repo_id = str(repo.id)
                repo_node_id = repo_id
                nodes[repo_id] = GraphNode(
                    id=repo_id,
                    type=GraphNodeType.REPOSITORY,
                    label=repo.full_name or repo.name,
                    metadata={
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "owner": repo.owner,
                        "default_branch": repo.default_branch,
                        "url": repo.url,
                        "service_id": s_id,
                    },
                )
                edge_key = (s_id, repo_id, GraphEdgeType.CONTAINS)
                edges[edge_key] = GraphEdge(
                    id=f"{s_id}->{repo_id}:{GraphEdgeType.CONTAINS.value}",
                    source=s_id,
                    target=repo_id,
                    type=GraphEdgeType.CONTAINS,
                )

        # 8. Retrieve symbols strictly for the latest snapshot (bulk query)
        symbols_query = (
            select(CodeSymbol)
            .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
            .where(RepositoryFile.snapshot_id == snapshot.id)
            .order_by(CodeSymbol.start_line.asc())
        )
        symbols_res = await session.execute(symbols_query)
        symbols = symbols_res.scalars().all()
        symbol_map: dict[uuid.UUID, CodeSymbol] = {s.id: s for s in symbols}

        # 9. Retrieve dependencies strictly for the latest snapshot (bulk query)
        deps_query = (
            select(CodeDependency)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .where(RepositoryFile.snapshot_id == snapshot.id)
            .order_by(CodeDependency.line_number.asc())
        )
        deps_res = await session.execute(deps_query)
        dependencies = deps_res.scalars().all()

        # 10. Build file nodes and link Repository -> File (CONTAINS)
        repo_id_str = repo_node_id
        for f in files:
            node_id = str(f.id)
            nodes[node_id] = GraphNode(
                id=node_id,
                type=GraphNodeType.FILE,
                label=f.path,
                metadata={
                    "path": f.path,
                    "filename": f.filename,
                    "extension": f.extension,
                    "language": f.language,
                    "line_count": f.line_count,
                    "size_bytes": f.size_bytes,
                },
            )
            if repo_id_str:
                edge_key = (repo_id_str, node_id, GraphEdgeType.CONTAINS)
                edges[edge_key] = GraphEdge(
                    id=f"{repo_id_str}->{node_id}:{GraphEdgeType.CONTAINS.value}",
                    source=repo_id_str,
                    target=node_id,
                    type=GraphEdgeType.CONTAINS,
                )

        # 7. Build symbol nodes and hierarchy / definition edges
        for s in symbols:
            sym_id = str(s.id)
            try:
                node_type = GraphNodeType(s.symbol_type.value)
            except (ValueError, KeyError):
                node_type = GraphNodeType.TYPE

            nodes[sym_id] = GraphNode(
                id=sym_id,
                type=node_type,
                label=s.name,
                metadata={
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "symbol_type": s.symbol_type.value,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "file_id": str(s.file_id),
                    "parent_symbol_id": str(s.parent_symbol_id) if s.parent_symbol_id else None,
                    **(s.symbol_metadata or {}),
                },
            )

            # Hierarchical containment: parent symbol -> child symbol
            if s.parent_symbol_id and s.parent_symbol_id in symbol_map:
                parent_id = str(s.parent_symbol_id)
                edge_key = (parent_id, sym_id, GraphEdgeType.CONTAINS)
                if edge_key not in edges:
                    edges[edge_key] = GraphEdge(
                        id=f"{parent_id}->{sym_id}:{GraphEdgeType.CONTAINS.value}",
                        source=parent_id,
                        target=sym_id,
                        type=GraphEdgeType.CONTAINS,
                        metadata={
                            "start_line": s.start_line,
                            "end_line": s.end_line,
                        },
                    )
            # Definition: file -> top-level symbol (or fallback if parent not in snapshot)
            elif s.file_id in file_map:
                file_id = str(s.file_id)
                edge_key = (file_id, sym_id, GraphEdgeType.DEFINES)
                if edge_key not in edges:
                    edges[edge_key] = GraphEdge(
                        id=f"{file_id}->{sym_id}:{GraphEdgeType.DEFINES.value}",
                        source=file_id,
                        target=sym_id,
                        type=GraphEdgeType.DEFINES,
                        metadata={
                            "start_line": s.start_line,
                            "end_line": s.end_line,
                        },
                    )

        # 8. Build dependency edges (internal and external)
        for dep in dependencies:
            if dep.source_file_id not in file_map:
                continue

            source_id = str(dep.source_file_id)

            # Internal file-to-file dependency
            if dep.target_file_id and dep.target_file_id in file_map:
                target_id = str(dep.target_file_id)
                edge_key = (source_id, target_id, GraphEdgeType.DEPENDS_ON)
                if edge_key not in edges:
                    edges[edge_key] = GraphEdge(
                        id=f"{source_id}->{target_id}:{GraphEdgeType.DEPENDS_ON.value}",
                        source=source_id,
                        target=target_id,
                        type=GraphEdgeType.DEPENDS_ON,
                        metadata={
                            "dependency_type": dep.dependency_type.value,
                            "line_number": dep.line_number,
                        },
                    )

            # External package dependency
            elif dep.external_package and dep.external_package.strip():
                pkg_name = dep.external_package.strip()
                pkg_node_id = f"pkg:{pkg_name}"

                # Deduplicate external package nodes
                if pkg_node_id not in nodes:
                    nodes[pkg_node_id] = GraphNode(
                        id=pkg_node_id,
                        type=GraphNodeType.EXTERNAL_PACKAGE,
                        label=pkg_name,
                        metadata={
                            "package_name": pkg_name,
                        },
                    )

                edge_key = (source_id, pkg_node_id, GraphEdgeType.DEPENDS_ON)
                if edge_key not in edges:
                    edges[edge_key] = GraphEdge(
                        id=f"{source_id}->{pkg_node_id}:{GraphEdgeType.DEPENDS_ON.value}",
                        source=source_id,
                        target=pkg_node_id,
                        type=GraphEdgeType.DEPENDS_ON,
                        metadata={
                            "dependency_type": dep.dependency_type.value,
                            "line_number": dep.line_number,
                            "external_package": pkg_name,
                        },
                    )

        node_list = list(nodes.values())
        edge_list = list(edges.values())

        return GraphResponse(
            nodes=node_list,
            edges=edge_list,
            snapshot_id=snapshot.id,
            total_nodes=len(node_list),
            total_edges=len(edge_list),
        )
