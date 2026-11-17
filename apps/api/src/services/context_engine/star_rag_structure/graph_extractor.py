"""
AST Function-Level Graph Extractor for Structure-Aware STAR-RAG.
Builds reliable directed function-to-function and class-to-class call graphs,
preserving source file paths, line ranges, symbol identities, and commit provenance.
"""

from __future__ import annotations

import ast
import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphNodeType,
    GraphRelationType,
)

logger = logging.getLogger(__name__)


class ASTFunctionCallVisitor(ast.NodeVisitor):
    """
    Traverses Python AST to extract functions, methods, classes, and their call sites.
    """

    def __init__(self, file_path: str, code_content: str):
        self.file_path = file_path
        self.code_content = code_content
        self.nodes: list[FunctionGraphNode] = []
        self.edges: list[FunctionGraphEdge] = []
        self.current_class: str | None = None
        self.current_function: str | None = None
        self.function_stack: list[str] = []
        self.imports: dict[str, str] = {}  # imported_name -> module_or_full_name

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            as_name = alias.asname or alias.name
            self.imports[as_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            as_name = alias.asname or alias.name
            target = f"{module}.{alias.name}" if module else alias.name
            self.imports[as_name] = target
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = node.name
        node_id = f"{self.file_path}::{class_name}"
        class_node = FunctionGraphNode(
            node_id=node_id,
            name=class_name,
            qualified_name=f"{self.file_path}:{class_name}",
            node_type=GraphNodeType.CLASS,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=f"class {class_name}",
        )
        self.nodes.append(class_node)

        # Inheritance edges
        for base in node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name:
                resolved_base = self.imports.get(base_name, base_name)
                target_id = f"external::{resolved_base}" if "." in resolved_base else f"{self.file_path}::{resolved_base}"
                self.edges.append(
                    FunctionGraphEdge(
                        source_id=node_id,
                        target_id=target_id,
                        relation_type=GraphRelationType.INHERITS,
                        line_number=node.lineno,
                        source_file=self.file_path,
                        metadata={"base_class": resolved_base},
                    )
                )

        prev_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        func_name = node.name
        is_method = self.current_class is not None
        node_type = GraphNodeType.METHOD if is_method else GraphNodeType.FUNCTION

        if is_method and self.current_class:
            qualified = f"{self.current_class}.{func_name}"
            node_id = f"{self.file_path}::{self.current_class}::{func_name}"
        else:
            qualified = func_name
            node_id = f"{self.file_path}::{func_name}"

        # Extract arg names for signature
        args = [a.arg for a in node.args.args]
        sig = f"def {func_name}({', '.join(args)})"

        func_node = FunctionGraphNode(
            node_id=node_id,
            name=func_name,
            qualified_name=qualified,
            node_type=node_type,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=sig,
        )
        self.nodes.append(func_node)

        # Record DEFINES edge from class or file
        if is_method and self.current_class:
            class_id = f"{self.file_path}::{self.current_class}"
            self.edges.append(
                FunctionGraphEdge(
                    source_id=class_id,
                    target_id=node_id,
                    relation_type=GraphRelationType.DEFINES,
                    line_number=node.lineno,
                    source_file=self.file_path,
                )
            )

        self.function_stack.append(node_id)
        prev_func = self.current_function
        self.current_function = node_id
        self.generic_visit(node)
        self.current_function = prev_func
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_function:
            callee_name = None
            module_qualifier = None

            if isinstance(node.func, ast.Name):
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    module_qualifier = node.func.value.id

            if callee_name:
                # Resolve target node ID
                target_id = None
                target_file = ""
                if module_qualifier and module_qualifier in self.imports:
                    mod = self.imports[module_qualifier]
                    target_id = f"{mod}::{callee_name}"
                    target_file = mod.replace(".", "/") + ".py"
                elif callee_name in self.imports:
                    target_id = f"{self.imports[callee_name]}"
                    target_file = self.imports[callee_name].split(".")[0] + ".py"
                else:
                    # Same file or unresolved local call
                    target_id = f"{self.file_path}::{callee_name}"
                    target_file = self.file_path

                self.edges.append(
                    FunctionGraphEdge(
                        source_id=self.current_function,
                        target_id=target_id,
                        relation_type=GraphRelationType.CALLS,
                        line_number=node.lineno,
                        source_file=self.file_path,
                        target_file=target_file,
                        metadata={
                            "callee_name": callee_name,
                            "module_qualifier": module_qualifier,
                        },
                    )
                )

        self.generic_visit(node)


class CodeGraphExtractor:
    """
    Constructs a normalized, directed FunctionGraph from source code strings,
    AST analysis, and existing PostgreSQL code_symbols and code_dependencies.
    """

    @staticmethod
    def extract_from_source(file_path: str, source_code: str) -> FunctionGraph:
        """Parses Python source code and extracts function/method/class nodes and calls."""
        graph = FunctionGraph()
        file_node = FunctionGraphNode(
            node_id=f"file::{file_path}",
            name=file_path.split("/")[-1],
            qualified_name=file_path,
            node_type=GraphNodeType.FILE,
            file_path=file_path,
            start_line=1,
            end_line=len(source_code.splitlines()) or 1,
        )
        graph.add_node(file_node)

        try:
            tree = ast.parse(source_code, filename=file_path)
            visitor = ASTFunctionCallVisitor(file_path, source_code)
            visitor.visit(tree)

            for node in visitor.nodes:
                graph.add_node(node)
                # Link file -> node via DEFINES
                graph.add_edge(
                    FunctionGraphEdge(
                        source_id=file_node.node_id,
                        target_id=node.node_id,
                        relation_type=GraphRelationType.DEFINES,
                        line_number=node.start_line,
                        source_file=file_path,
                    )
                )

            for edge in visitor.edges:
                graph.add_edge(edge)

        except SyntaxError as e:
            logger.debug("Syntax error parsing %s for AST graph: %s", file_path, e)
        except Exception as e:
            logger.warning("Error extracting AST function graph for %s: %s", file_path, e)

        return graph

    @staticmethod
    async def build_graph_for_snapshot(
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        file_ids: list[uuid.UUID] | None = None,
        max_files: int = 50,
    ) -> FunctionGraph:
        """
        Builds a combined FunctionGraph from persisted database records:
        RepositoryFile, CodeSymbol, and CodeDependency.
        """
        graph = FunctionGraph()

        # 1. Query files
        file_query = select(RepositoryFile).where(RepositoryFile.snapshot_id == snapshot_id)
        if file_ids:
            file_query = file_query.where(RepositoryFile.id.in_(file_ids))
        file_query = file_query.limit(max_files)

        file_res = await session.execute(file_query)
        files = file_res.scalars().all()
        file_map: dict[uuid.UUID, RepositoryFile] = {f.id: f for f in files}

        for f in files:
            f_node = FunctionGraphNode(
                node_id=f"file:{f.id}",
                name=f.filename,
                qualified_name=f.path,
                node_type=GraphNodeType.FILE,
                file_path=f.path,
                start_line=1,
                end_line=f.line_count or 1,
                file_id=f.id,
            )
            graph.add_node(f_node)

        if not files:
            return graph

        target_file_ids = list(file_map.keys())

        # 2. Query symbols
        sym_query = (
            select(CodeSymbol)
            .where(CodeSymbol.file_id.in_(target_file_ids))
            .order_by(CodeSymbol.start_line.asc())
        )
        sym_res = await session.execute(sym_query)
        symbols = sym_res.scalars().all()

        symbol_node_map: dict[uuid.UUID, str] = {}
        for s in symbols:
            f = file_map.get(s.file_id)
            f_path = f.path if f else ""
            node_id = f"sym:{s.id}"
            symbol_node_map[s.id] = node_id

            # Map SymbolType to GraphNodeType
            n_type = GraphNodeType.FUNCTION
            if s.symbol_type.value == "CLASS":
                n_type = GraphNodeType.CLASS
            elif s.symbol_type.value == "METHOD":
                n_type = GraphNodeType.METHOD

            s_node = FunctionGraphNode(
                node_id=node_id,
                name=s.name,
                qualified_name=s.qualified_name or f"{f_path}:{s.name}",
                node_type=n_type,
                file_path=f_path,
                start_line=s.start_line,
                end_line=s.end_line,
                file_id=s.file_id,
                symbol_id=s.id,
                signature=s.qualified_name or s.name,
                metadata=s.symbol_metadata or {},
            )
            graph.add_node(s_node)

            # Link file -> symbol
            graph.add_edge(
                FunctionGraphEdge(
                    source_id=f"file:{s.file_id}",
                    target_id=node_id,
                    relation_type=GraphRelationType.DEFINES,
                    line_number=s.start_line,
                    source_file=f_path,
                )
            )

            # Link parent symbol -> child symbol
            if s.parent_symbol_id and s.parent_symbol_id in symbol_node_map:
                graph.add_edge(
                    FunctionGraphEdge(
                        source_id=symbol_node_map[s.parent_symbol_id],
                        target_id=node_id,
                        relation_type=GraphRelationType.DEFINES,
                        line_number=s.start_line,
                        source_file=f_path,
                    )
                )

        # 3. Query dependencies
        dep_query = select(CodeDependency).where(
            or_(
                CodeDependency.source_file_id.in_(target_file_ids),
                CodeDependency.target_file_id.in_(target_file_ids),
            )
        )
        dep_res = await session.execute(dep_query)
        deps = dep_res.scalars().all()

        for d in deps:
            src_f = file_map.get(d.source_file_id)
            tgt_f = file_map.get(d.target_file_id) if d.target_file_id else None

            src_id = f"file:{d.source_file_id}"
            tgt_id = f"file:{d.target_file_id}" if d.target_file_id else f"pkg:{d.external_package}"

            if tgt_id not in graph.nodes and d.external_package:
                graph.add_node(
                    FunctionGraphNode(
                        node_id=tgt_id,
                        name=d.external_package,
                        qualified_name=d.external_package,
                        node_type=GraphNodeType.MODULE,
                        file_path=d.external_package,
                    )
                )

            graph.add_edge(
                FunctionGraphEdge(
                    source_id=src_id,
                    target_id=tgt_id,
                    relation_type=GraphRelationType.IMPORTS,
                    line_number=d.line_number,
                    source_file=src_f.path if src_f else "",
                    target_file=tgt_f.path if tgt_f else (d.external_package or ""),
                )
            )

        return graph
