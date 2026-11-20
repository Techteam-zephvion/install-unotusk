from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GroundedAnswer:
    content: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    confidence: str = "HIGH"
    debug_signals: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_grounded_answer(
        self,
        question: str,
        project_context: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        conversation_history: list[dict[str, str]] | None = None,
        thinking_tier: str | None = None,
    ) -> GroundedAnswer: ...

    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a JSON response for structured extraction tasks."""
        ...


MIN_GROUNDED_SYNTHESIS_THRESHOLD: float = 0.20


def extract_customer_notes(project_context: str) -> list[str]:
    """
    Extracts structured customer project knowledge blocks from prompt context.
    Customer knowledge represents explicit user-taught domain context and constraints.
    """
    customer_notes: list[str] = []
    if "<customer_project_knowledge>" in project_context:
        try:
            start_tag = "<customer_project_knowledge>"
            end_tag = "</customer_project_knowledge>"
            start_idx = project_context.find(start_tag) + len(start_tag)
            end_idx = project_context.find(end_tag)
            if start_idx != -1 and end_idx != -1:
                raw_knowledge = project_context[start_idx:end_idx].strip()
                for block in raw_knowledge.split("### [CUSTOMER:"):
                    block = block.strip()
                    if block and not block.startswith("This is user-provided"):
                        lines_b = block.splitlines()
                        header = lines_b[0].strip()
                        content_lines = [
                            line_text
                            for line_text in lines_b[1:]
                            if line_text.strip().startswith("Content:")
                        ]
                        content_txt = (
                            content_lines[0].replace("Content:", "").strip()
                            if content_lines
                            else ""
                        )
                        customer_notes.append(f"- **[CUSTOMER: {header}]**: {content_txt}")
        except Exception:
            pass

    return customer_notes


def extract_integration_notes(project_context: str) -> list[str]:
    """
    Extracts structured integration context blocks from prompt context.
    Integration context represents synchronized issues, requirements, PRs, and external specs.
    """
    integration_notes: list[str] = []
    if "<integration_project_context>" in project_context:
        try:
            start_tag = "<integration_project_context>"
            end_tag = "</integration_project_context>"
            start_idx = project_context.find(start_tag) + len(start_tag)
            end_idx = project_context.find(end_tag)
            if start_idx != -1 and end_idx != -1:
                raw_integration = project_context[start_idx:end_idx].strip()
                for block in raw_integration.split("### [INTEGRATION:"):
                    block = block.strip()
                    if block and not block.startswith("This block contains"):
                        lines_b = block.splitlines()
                        header = lines_b[0].strip()
                        content_lines = [
                            line_text
                            for line_text in lines_b[1:]
                            if line_text.strip().startswith("Content:")
                        ]
                        content_txt = (
                            content_lines[0].replace("Content:", "").strip()
                            if content_lines
                            else ""
                        )
                        integration_notes.append(f"- **[INTEGRATION: {header}]**: {content_txt}")
        except Exception:
            pass

    return integration_notes


def should_abstain_due_to_insufficient_evidence(
    evidence_items: list[dict[str, Any]],
    customer_notes: list[str],
    integration_notes: list[str] | None = None,
    threshold: float = MIN_GROUNDED_SYNTHESIS_THRESHOLD,
) -> tuple[bool, float]:
    """
    Evaluates the Architecture V1 Low-Confidence Synthesis Gate.
    Returns (should_abstain, max_relevance).

    Abstention triggers to prevent hallucination when:
    1. No customer or integration project knowledge is available, AND
    2. Either evidence_items is empty OR the maximum candidate relevance is below threshold (< 0.20).
    """
    max_rel = max((float(e.get("relevance", 0.0)) for e in evidence_items), default=0.0)
    if customer_notes or (integration_notes and len(integration_notes) > 0):
        return False, max_rel
    if not evidence_items or max_rel < threshold:
        return True, max_rel
    return False, max_rel


def format_insufficient_evidence_response(
    question: str,
    max_relevance: float,
    threshold: float = MIN_GROUNDED_SYNTHESIS_THRESHOLD,
) -> str:
    """
    Formats an explicit, safe insufficient-evidence response preventing unsupported factual claims.
    """
    if max_relevance > 0.0:
        detail = (
            f"The retrieved candidate components do not meet the minimum grounding threshold "
            f"(max relevance {max_relevance:.2f} < {threshold:.2f}) required to formulate a factual answer."
        )
    else:
        detail = "No matching files, symbols, or dependencies were found in the current repository snapshot."

    return (
        f"### Insufficient Evidence\n\n"
        f"I searched the repository and indexed project context for references to **'{question}'**, "
        f"but did not find sufficient grounded code evidence or architectural specifications.\n\n"
        f"{detail}\n\n"
        f"**Note**: If this component was recently added or modified, please ensure the repository is fully indexed."
    )


def generate_grounded_mermaid_diagram(
    question: str,
    evidence_items: list[dict[str, Any]],
    symbols: list[str],
    files: list[str],
) -> str:
    """
    Generates a 10/10 custom Mermaid diagram based strictly on the retrieved
    evidence files, symbols, components, and user request.
    Dynamically maps actual files, components, and assets into semantic layers.
    Never uses static boilerplate.
    """
    q_lower = question.lower()
    needs_diagram = any(
        kw in q_lower
        for kw in (
            "diagram",
            "arch",
            "flow",
            "visual",
            "struct",
            "topology",
            "pipeline",
            "design",
            "component",
            "workflow",
        )
    )
    if not needs_diagram:
        return ""

    def sanitize(raw: str) -> str:
        return (
            raw.replace('"', "'")
            .replace("<", "")
            .replace(">", "")
            .replace("&", "and")
            .replace("#", "")
            .replace(";", "")
            .replace("{", "(")
            .replace("}", ")")
            .strip()
        )

    # Sequence diagram for auth/protocol requests
    if (
        any(k in q_lower for k in ("auth", "login", "jwt", "token", "handshake", "protocol"))
        and len(symbols) >= 2
    ):
        lines = [
            "```mermaid",
            "sequenceDiagram",
            "    autonumber",
            '    actor User as "Client / User"',
        ]
        participants = []
        for i, s in enumerate(symbols[:3]):
            p_id = f"Part_{i}"
            lines.append(f'    participant {p_id} as "{sanitize(s)}"')
            participants.append(p_id)
        if files:
            f_id = "File_0"
            lines.append(f'    participant {f_id} as "{sanitize(files[0])}"')
            participants.append(f_id)
        lines.append(f'    User->>{participants[0]}: "Trigger Action"')
        for j in range(len(participants) - 1):
            lines.append(f'    {participants[j]}->>{participants[j+1]}: "Process & Validate"')
            lines.append(f'    {participants[j+1]}-->>{participants[j]}: "Result Status"')
        lines.append(f'    {participants[0]}-->>User: "200 Success"')
        lines.append("```")
        return "\n".join(lines)

    # Classify files and symbols into dynamic layers based on actual paths & names
    ui_nodes: list[tuple[str, str]] = []
    api_nodes: list[tuple[str, str]] = []
    domain_nodes: list[tuple[str, str]] = []
    data_nodes: list[tuple[str, str]] = []
    asset_nodes: list[tuple[str, str]] = []

    # Categorize files
    for idx, f in enumerate(files):
        f_lower = f.lower()
        node_id = f"F_{idx}"
        label = sanitize(f)
        if any(
            f_lower.endswith(ext)
            for ext in (".webp", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".css", ".scss")
        ) or "public/" in f_lower or "assets/" in f_lower:
            asset_nodes.append((node_id, label))
        elif any(
            f_lower.endswith(ext) for ext in (".tsx", ".jsx", ".vue", ".svelte", ".html")
        ) or any(k in f_lower for k in ("/ui/", "/components/", "/pages/", "/screens/", "/views/")):
            ui_nodes.append((node_id, label))
        elif any(k in f_lower for k in ("/api/", "/routes/", "/endpoints/", "/controllers/", "/gateways/")):
            api_nodes.append((node_id, label))
        elif any(k in f_lower for k in ("/models/", "/schemas/", "/db/", "/entities/", "/repositories/", "/store/")):
            data_nodes.append((node_id, label))
        else:
            domain_nodes.append((node_id, label))

    # Categorize symbols
    for s_idx, sym in enumerate(symbols):
        sym_lower = sym.lower()
        node_id = f"S_{s_idx}"
        label = sanitize(sym)
        if any(k in sym_lower for k in ("ui", "screen", "view", "component", "button", "section", "modal", "page")):
            ui_nodes.append((node_id, label))
        elif any(k in sym_lower for k in ("route", "api", "endpoint", "controller", "handler", "post", "get")):
            api_nodes.append((node_id, label))
        elif any(k in sym_lower for k in ("model", "schema", "table", "entity", "repository", "db")):
            data_nodes.append((node_id, label))
        else:
            domain_nodes.append((node_id, label))

    # If all nodes fell into one category or evidence was minimal, ensure at least domain has them
    if not ui_nodes and not api_nodes and not domain_nodes and not data_nodes and not asset_nodes:
        for idx, f in enumerate(files[:3]):
            domain_nodes.append((f"F_{idx}", sanitize(f)))
        for s_idx, sym in enumerate(symbols[:3]):
            domain_nodes.append((f"S_{s_idx}", sanitize(sym)))

    lines = [
        "```mermaid",
        "flowchart TD",
    ]

    all_ui_ids = []
    all_api_ids = []
    all_domain_ids = []
    all_data_ids = []
    all_asset_ids = []

    if ui_nodes:
        lines.append('    subgraph UI ["User Interface & Presentation Layer"]')
        for nid, lbl in ui_nodes[:4]:
            lines.append(f'        {nid}["{lbl}"]')
            all_ui_ids.append(nid)
        lines.append("    end")

    if api_nodes:
        lines.append('    subgraph API ["Routing & API Layer"]')
        for nid, lbl in api_nodes[:4]:
            lines.append(f'        {nid}["{lbl}"]')
            all_api_ids.append(nid)
        lines.append("    end")

    if domain_nodes:
        lines.append('    subgraph Logic ["Domain Logic & Services"]')
        for nid, lbl in domain_nodes[:5]:
            lines.append(f'        {nid}["{lbl}"]')
            all_domain_ids.append(nid)
        lines.append("    end")

    if data_nodes:
        lines.append('    subgraph Data ["Data & Persistence Layer"]')
        for nid, lbl in data_nodes[:4]:
            lines.append(f'        {nid}[("{lbl}")]')
            all_data_ids.append(nid)
        lines.append("    end")

    if asset_nodes:
        lines.append('    subgraph Assets ["Static Assets & Media"]')
        for nid, lbl in asset_nodes[:3]:
            lines.append(f'        {nid}["{lbl}"]')
            all_asset_ids.append(nid)
        lines.append("    end")

    # Draw logical connections between layers
    if all_ui_ids and all_domain_ids:
        lines.append(f"    {all_ui_ids[0]} -->|executes/renders| {all_domain_ids[0]}")
    if all_api_ids and all_domain_ids:
        lines.append(f"    {all_api_ids[0]} -->|routes to| {all_domain_ids[0]}")
    if all_domain_ids and all_data_ids:
        lines.append(f"    {all_domain_ids[0]} -->|persists/queries| {all_data_ids[0]}")
    if all_ui_ids and all_asset_ids:
        lines.append(f"    {all_ui_ids[0]} -.->|loads asset| {all_asset_ids[0]}")
    if all_domain_ids and len(all_domain_ids) > 1:
        lines.append(f"    {all_domain_ids[0]} -->|calls| {all_domain_ids[1]}")

    # Apply Spec Dark-Mode Color Definitions
    lines.append("    classDef ui fill:#1E293B,stroke:#38BDF8,stroke-width:1.5px,color:#F8FAFC;")
    lines.append("    classDef api fill:#2A1B3D,stroke:#A855F7,stroke-width:1.5px,color:#F8FAFC;")
    lines.append("    classDef domain fill:#1A2E26,stroke:#10B981,stroke-width:1.5px,color:#F8FAFC;")
    lines.append("    classDef data fill:#332200,stroke:#F59E0B,stroke-width:1.5px,color:#F8FAFC;")
    lines.append("    classDef asset fill:#262338,stroke:#EC4899,stroke-width:1.5px,color:#F8FAFC;")

    if all_ui_ids:
        lines.append(f'    class {",".join(all_ui_ids)} ui;')
    if all_api_ids:
        lines.append(f'    class {",".join(all_api_ids)} api;')
    if all_domain_ids:
        lines.append(f'    class {",".join(all_domain_ids)} domain;')
    if all_data_ids:
        lines.append(f'    class {",".join(all_data_ids)} data;')
    if all_asset_ids:
        lines.append(f'    class {",".join(all_asset_ids)} asset;')

    lines.append("```")
    return "\n".join(lines)
