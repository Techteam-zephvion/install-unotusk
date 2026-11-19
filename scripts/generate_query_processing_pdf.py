#!/usr/bin/env python3
"""
Unotusk Query Processing Lifecycle PDF Generator
Generates a professional, multi-page architectural PDF explaining how data is processed after a user query is given.
"""

import os
import sys

class PDFCanvas:
    """A lightweight, pure-Python PDF 1.4 canvas for generating formatted multi-page documents."""
    
    def __init__(self, width=595.28, height=841.89):
        self.width = width
        self.height = height
        self.pages = []
        self.current_stream = []
        self.fonts = {
            "/F1": "/Helvetica",
            "/F2": "/Helvetica-Bold",
            "/F3": "/Helvetica-Oblique",
            "/F4": "/Courier",
            "/F5": "/Courier-Bold",
        }
        self.current_page_num = 0

    def new_page(self):
        if self.current_stream:
            self.pages.append("".join(self.current_stream))
            self.current_stream = []
        self.current_page_num += 1
        # Set default graphics state
        self.set_color_rgb(0.1, 0.1, 0.1, fill=False)
        self.set_color_rgb(0.1, 0.1, 0.1, fill=True)

    def set_color_rgb(self, r, g, b, fill=True):
        cmd = "rg" if fill else "RG"
        self.current_stream.append(f"{r:.3f} {g:.3f} {b:.3f} {cmd}\n")

    def set_line_width(self, width):
        self.current_stream.append(f"{width:.2f} w\n")

    def rect(self, x, y, w, h, fill=False, stroke=True):
        op = "B" if (fill and stroke) else ("f" if fill else "S")
        self.current_stream.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}\n")

    def round_rect(self, x, y, w, h, r=4, fill=True, stroke=False):
        # Approximate rounded rectangle with polygon/rect
        self.rect(x, y, w, h, fill=fill, stroke=stroke)

    def line(self, x1, y1, x2, y2):
        self.current_stream.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n")

    def draw_text(self, x, y, text, font="/F1", size=10, color=(0.1, 0.1, 0.1)):
        self.set_color_rgb(*color, fill=True)
        # Clean text to ASCII compatibility
        clean_text = (
            text.replace("—", "--")
            .replace("–", "-")
            .replace("•", "*")
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        self.current_stream.append(
            f"BT\n{font} {size} Tf\n{x:.2f} {y:.2f} Td\n({clean_text}) Tj\nET\n"
        )

    def draw_wrapped_text(self, x, y, text, width, font="/F1", size=10, line_height=14, color=(0.2, 0.2, 0.2)):
        words = text.split(" ")
        lines = []
        curr_line = []
        # Approximate character width based on font
        char_w = size * 0.52 if "Courier" not in font else size * 0.60

        for word in words:
            test_line = " ".join(curr_line + [word])
            if len(test_line) * char_w > width and curr_line:
                lines.append(" ".join(curr_line))
                curr_line = [word]
            else:
                curr_line.append(word)
        if curr_line:
            lines.append(" ".join(curr_line))

        cur_y = y
        for line in lines:
            self.draw_text(x, cur_y, line, font=font, size=size, color=color)
            cur_y -= line_height
        return cur_y

    def save(self, filepath):
        if self.current_stream:
            self.pages.append("".join(self.current_stream))
            self.current_stream = []

        total_pages = len(self.pages)
        objects = []
        
        # Object 1: Catalog
        # Object 2: Pages root
        # Object 3..2+N: Page objects
        # Object 3+N..2+2N: Content stream objects
        # Font objects follow

        pages_kids = []
        page_obj_ids = []
        content_obj_ids = []

        # We will build objects sequentially
        # Obj 1: Catalog (id 1)
        # Obj 2: Pages (id 2)
        next_id = 3
        for i in range(total_pages):
            page_obj_ids.append(next_id)
            next_id += 1
            content_obj_ids.append(next_id)
            next_id += 1

        font_obj_ids = {}
        for fname in self.fonts:
            font_obj_ids[fname] = next_id
            next_id += 1

        # Catalog
        catalog = f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Pages root
        kids_str = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
        pages_root = f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>\nendobj\n"

        pdf_parts = ["%PDF-1.4\n", catalog, pages_root]
        obj_offsets = {1: len(pdf_parts[0]), 2: len(pdf_parts[0]) + len(catalog)}

        # Build fonts resource dict
        font_res_str = " ".join([f"{fname} {font_obj_ids[fname]} 0 R" for fname in self.fonts])

        curr_offset = obj_offsets[2] + len(pages_root)

        # Page objects and contents
        for i in range(total_pages):
            p_id = page_obj_ids[i]
            c_id = content_obj_ids[i]
            stream_data = self.pages[i]
            stream_len = len(stream_data.encode("utf-8"))

            page_str = (
                f"{p_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Contents {c_id} 0 R /Resources << /Font << {font_res_str} >> >> >>\n"
                f"endobj\n"
            )
            obj_offsets[p_id] = curr_offset
            pdf_parts.append(page_str)
            curr_offset += len(page_str)

            content_str = (
                f"{c_id} 0 obj\n"
                f"<< /Length {stream_len} >>\n"
                f"stream\n"
                f"{stream_data}"
                f"endstream\n"
                f"endobj\n"
            )
            obj_offsets[c_id] = curr_offset
            pdf_parts.append(content_str)
            curr_offset += len(content_str)

        # Font objects
        for fname, base_font in self.fonts.items():
            f_id = font_obj_ids[fname]
            font_str = f"{f_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont {base_font} >>\nendobj\n"
            obj_offsets[f_id] = curr_offset
            pdf_parts.append(font_str)
            curr_offset += len(font_str)

        # XRef table
        xref_offset = curr_offset
        total_objs = next_id
        xref = [f"xref\n0 {total_objs}\n0000000000 65535 f \n"]
        for oid in range(1, total_objs):
            off = obj_offsets[oid]
            xref.append(f"{off:010d} 00000 n \n")

        trailer = (
            f"trailer\n"
            f"<< /Size {total_objs} /Root 1 0 R >>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        )
        pdf_parts.append("".join(xref))
        pdf_parts.append(trailer)

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="latin-1", errors="replace") as f:
            f.write("".join(pdf_parts))
        print(f"Generated PDF with {total_pages} pages: {filepath}")


def draw_page_chrome(c, page_title, subtitle, page_num, total_pages=4):
    """Draws standardized header, branding bar, and footer on each page."""
    # Top banner bar
    c.set_color_rgb(0.094, 0.094, 0.086, fill=True) # Unotusk Warm Dark #181816
    c.rect(0, 785, 595.28, 56.89, fill=True, stroke=False)

    # Accent hairline
    c.set_color_rgb(0.85, 0.45, 0.15, fill=True) # Terracotta accent
    c.rect(0, 783, 595.28, 2.5, fill=True, stroke=False)

    # Logo / Product Name
    c.draw_text(40, 810, "UNOTUSK", font="/F2", size=15, color=(1.0, 1.0, 1.0))
    c.draw_text(118, 810, "|  PROJECT INTELLIGENCE", font="/F1", size=10, color=(0.8, 0.8, 0.78))
    
    # Header tag badge
    c.set_color_rgb(0.22, 0.22, 0.20, fill=True)
    c.round_rect(440, 804, 115, 18, r=3, fill=True, stroke=False)
    c.draw_text(447, 809, "QUERY DATA PIPELINE", font="/F2", size=7.5, color=(0.95, 0.7, 0.35))

    # Page Title & Subtitle
    c.draw_text(40, 755, page_title, font="/F2", size=16, color=(0.12, 0.12, 0.12))
    c.draw_text(40, 740, subtitle, font="/F3", size=9.5, color=(0.45, 0.45, 0.45))
    c.set_color_rgb(0.88, 0.88, 0.86, fill=False)
    c.set_line_width(0.75)
    c.line(40, 732, 555.28, 732)

    # Footer
    c.set_color_rgb(0.9, 0.9, 0.88, fill=False)
    c.set_line_width(0.5)
    c.line(40, 42, 555.28, 42)
    c.draw_text(40, 30, "Unotusk Architecture Specification — Confidential & Single-Tenant Local Deployment", font="/F1", size=8, color=(0.55, 0.55, 0.55))
    c.draw_text(500, 30, f"Page {page_num} of {total_pages}", font="/F2", size=8, color=(0.4, 0.4, 0.4))


def generate_query_processing_pdf(output_path):
    c = PDFCanvas(width=595.28, height=841.89)

    # =========================================================================
    # PAGE 1: EXECUTIVE WORKFLOW & HIGH-LEVEL PIPELINE
    # =========================================================================
    c.new_page()
    draw_page_chrome(
        c,
        page_title="1. Executive Lifecycle & End-to-End Pipeline",
        subtitle="Chronological flow of an architectural user query from Desktop UI to Grounded LLM Response",
        page_num=1,
        total_pages=4,
    )

    y = 715
    intro_p = (
        "When an engineer asks a question in the Unotusk Desktop Client (e.g. 'How does authentication middleware handle "
        "expired tokens on the features branch?'), the system does NOT pass raw files or rely on shallow README keyword "
        "lookups. Instead, it executes an evidence-grounded, 6-stage semantic processing pipeline with sub-second retrieval, "
        "AST symbol graph expansion, branch isolation, and multi-signal ranking."
    )
    y = c.draw_wrapped_text(40, y, intro_p, width=515, font="/F1", size=9.5, line_height=13.5, color=(0.2, 0.2, 0.2))

    y -= 10
    # Big Architecture Pipeline Diagram (Visual Cards Flow)
    stages = [
        ("STAGE 1", "Query Decomposition & Branch Resolution", "Extracts keywords, symbols, paths, and filters active branch snapshot.", (0.96, 0.96, 0.97)),
        ("STAGE 2", "Multi-Signal Candidate Retrieval", "Queries PostgreSQL with pgvector cosine similarity + AST symbol SQL.", (0.94, 0.96, 0.98)),
        ("STAGE 3", "Structural AST Graph Expansion", "Traverses 1-hop and 2-hop caller/callee relations via CodeDependency.", (0.94, 0.97, 0.95)),
        ("STAGE 4", "Multi-Signal Ranking & Code Boost", "Demotes READMEs (0.4x) and boosts AST classes/functions (1.8x).", (0.98, 0.95, 0.93)),
        ("STAGE 5", "Context Assembly & Token Budgeting", "Builds macro-skeleton, ranked chunks, customer ADRs under 6,000 tokens.", (0.97, 0.94, 0.97)),
        ("STAGE 6", "Grounded LLM Synthesis & Verification", "Synthesizes answer with exact file/line citations and verification checks.", (0.93, 0.97, 0.98)),
    ]

    card_y = y - 8
    for idx, (st_num, title, desc, bg_color) in enumerate(stages):
        # Card background
        c.set_color_rgb(*bg_color, fill=True)
        c.round_rect(40, card_y - 48, 515, 48, r=4, fill=True, stroke=False)
        # Border
        c.set_color_rgb(0.82, 0.84, 0.86, fill=False)
        c.set_line_width(0.7)
        c.rect(40, card_y - 48, 515, 48, fill=False, stroke=True)

        # Stage badge
        c.set_color_rgb(0.2, 0.25, 0.32, fill=True)
        c.round_rect(50, card_y - 30, 60, 16, r=2, fill=True, stroke=False)
        c.draw_text(56, card_y - 25, st_num, font="/F2", size=7.5, color=(1, 1, 1))

        # Title and description
        c.draw_text(120, card_y - 25, title, font="/F2", size=10, color=(0.12, 0.14, 0.18))
        c.draw_text(120, card_y - 39, desc, font="/F1", size=8.5, color=(0.35, 0.38, 0.42))

        # Down arrow connector (except for last)
        if idx < len(stages) - 1:
            c.set_color_rgb(0.65, 0.68, 0.72, fill=False)
            c.set_line_width(1.2)
            c.line(297, card_y - 48, 297, card_y - 56)
            card_y -= 57
        else:
            card_y -= 50

    y = card_y - 12
    # Section: Key Architectural Principles
    c.draw_text(40, y, "Core Tenets of Query Intelligence:", font="/F2", size=11, color=(0.15, 0.15, 0.15))
    y -= 14

    tenets = [
        ("• Zero Hallucination Policy: ", "The LLM synthesizes answers strictly grounded on retrieved evidence items with exact line numbers."),
        ("• AST Code Superiority: ", "Actual source code chunks outrank Markdown documentation to prevent superficial answers."),
        ("• Branch Isolation: ", "Developer feature branches (e.g. 'features', 'checkout') are isolated from 'main' snapshot data."),
        ("• Multi-Tenant Data Plane: ", "Every query is strictly constrained to the user's organization, project, and current conversation thread.")
    ]
    for b_title, b_desc in tenets:
        c.draw_text(45, y, b_title, font="/F2", size=8.5, color=(0.18, 0.18, 0.18))
        tw = len(b_title) * 8.5 * 0.52
        c.draw_text(45 + tw, y, b_desc, font="/F1", size=8.5, color=(0.3, 0.3, 0.3))
        y -= 13

    # =========================================================================
    # PAGE 2: STAGES 1 & 2 — QUERY ANALYSIS & CANDIDATE RETRIEVAL
    # =========================================================================
    c.new_page()
    draw_page_chrome(
        c,
        page_title="2. Query Decomposition & Tri-Signal Retrieval",
        subtitle="How user natural language is parsed and matched against pgvector, AST symbols, and file paths",
        page_num=2,
        total_pages=4,
    )

    y = 715
    c.draw_text(40, y, "Stage 1: Query Analysis & Branch Resolution", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16
    s1_text = (
        "When a request arrives at POST /api/v1/projects/{project_id}/ask with a GroundedAskRequest payload, the system "
        "first invokes analyze_query_async(). The query is analyzed across five orthogonal dimensions:"
    )
    y = c.draw_wrapped_text(40, y, s1_text, width=515, font="/F1", size=9, line_height=13, color=(0.25, 0.25, 0.25))

    y -= 8
    # 2-column breakdown of query analysis signals
    col1_x, col2_x = 45, 290
    c.set_color_rgb(0.97, 0.97, 0.97, fill=True)
    c.rect(40, y - 75, 515, 75, fill=True, stroke=False)
    c.set_color_rgb(0.85, 0.85, 0.85, fill=False)
    c.rect(40, y - 75, 515, 75, fill=False, stroke=True)

    c.draw_text(col1_x, y - 16, "1. Target Symbols: Extracts classes, functions (e.g. 'AuthMiddleware')", font="/F2", size=8, color=(0.15, 0.15, 0.15))
    c.draw_text(col1_x, y - 32, "2. File Path Clues: Identifies paths or extensions ('src/auth', '.py')", font="/F2", size=8, color=(0.15, 0.15, 0.15))
    c.draw_text(col1_x, y - 48, "3. Concept Synonyms: Expands domain keywords ('jwt' -> 'token', 'auth')", font="/F2", size=8, color=(0.15, 0.15, 0.15))
    c.draw_text(col1_x, y - 64, "4. Temporal Intent: Detects commit queries ('recent changes', 'git diff')", font="/F2", size=8, color=(0.15, 0.15, 0.15))

    c.draw_text(col2_x, y - 16, "Branch Snapshot Scoping:", font="/F2", size=8.5, color=(0.85, 0.35, 0.1))
    c.draw_text(col2_x, y - 30, "If payload.branch is specified (e.g. 'features'):", font="/F1", size=8, color=(0.3, 0.3, 0.3))
    c.draw_text(col2_x, y - 44, "SELECT * FROM repository_snapshots WHERE branch = :branch", font="/F4", size=7.5, color=(0.1, 0.3, 0.6))
    c.draw_text(col2_x, y - 58, "If branch is omitted, it defaults to the latest completed 'main' snapshot.", font="/F1", size=7.5, color=(0.4, 0.4, 0.4))

    y -= 95
    c.draw_text(40, y, "Stage 2: Tri-Signal Parallel Database Retrieval", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16
    s2_text = (
        "Rather than issuing a single embedding search, Unotusk dispatches three complementary signals in parallel against "
        "PostgreSQL 16 to guarantee both semantic depth and exact symbol precision:"
    )
    y = c.draw_wrapped_text(40, y, s2_text, width=515, font="/F1", size=9, line_height=13, color=(0.25, 0.25, 0.25))

    y -= 10
    # SQL Signals Table
    table_headers = [("Signal", 90), ("Mechanism", 140), ("Database Query Target", 185), ("Target Match", 100)]
    tx = 40
    c.set_color_rgb(0.2, 0.22, 0.26, fill=True)
    c.rect(40, y - 18, 515, 18, fill=True, stroke=False)
    for th, tw in table_headers:
        c.draw_text(tx + 6, y - 13, th, font="/F2", size=8, color=(1, 1, 1))
        tx += tw

    rows = [
        ("Signal A: Vector RAG", "Dense semantic similarity", "code_chunks.embedding <=> query_vec", "High-level concept intent"),
        ("Signal B: AST Symbols", "Exact & prefix symbol match", "code_symbols.name ILIKE :sym", "Classes, functions, methods"),
        ("Signal C: Path Index", "File hierarchy prefix match", "repository_files.path ILIKE :path", "Modules, packages, routes"),
    ]
    ry = y - 18
    for idx, (sig, mech, sql, mat) in enumerate(rows):
        bg = (0.97, 0.97, 0.98) if idx % 2 == 0 else (1.0, 1.0, 1.0)
        c.set_color_rgb(*bg, fill=True)
        c.rect(40, ry - 22, 515, 22, fill=True, stroke=False)
        c.set_color_rgb(0.88, 0.88, 0.9, fill=False)
        c.line(40, ry - 22, 555, ry - 22)

        c.draw_text(46, ry - 15, sig, font="/F2", size=8, color=(0.15, 0.15, 0.15))
        c.draw_text(136, ry - 15, mech, font="/F1", size=8, color=(0.3, 0.3, 0.3))
        c.draw_text(276, ry - 15, sql, font="/F4", size=7.5, color=(0.1, 0.3, 0.6))
        c.draw_text(461, ry - 15, mat, font="/F3", size=7.5, color=(0.35, 0.35, 0.35))
        ry -= 22

    y = ry - 18
    # Retrieval SQL Code Block Box
    c.draw_text(40, y, "Exact Vector Cosine Retrieval Query (PostgreSQL + pgvector):", font="/F2", size=10, color=(0.15, 0.15, 0.15))
    y -= 12

    sql_box = (
        "SELECT c.id, c.file_path, c.start_line, c.end_line, c.content, c.symbol_type,\n"
        "       1 - (c.embedding <=> :query_vector) AS cosine_similarity\n"
        "FROM code_chunks c\n"
        "JOIN repository_files f ON f.id = c.file_id\n"
        "WHERE f.snapshot_id = :active_snapshot_id\n"
        "ORDER BY c.embedding <=> :query_vector ASC\n"
        "LIMIT 40;"
    )
    c.set_color_rgb(0.96, 0.96, 0.97, fill=True)
    c.rect(40, y - 82, 515, 82, fill=True, stroke=False)
    c.set_color_rgb(0.8, 0.83, 0.88, fill=False)
    c.rect(40, y - 82, 515, 82, fill=False, stroke=True)

    sy = y - 14
    for line in sql_box.split("\n"):
        c.draw_text(50, sy, line, font="/F4", size=8, color=(0.1, 0.25, 0.45))
        sy -= 11

    # =========================================================================
    # PAGE 3: STAGES 3 & 4 — GRAPH EXPANSION & MULTI-SIGNAL RANKING
    # =========================================================================
    c.new_page()
    draw_page_chrome(
        c,
        page_title="3. AST Graph Expansion & Multi-Signal Ranking",
        subtitle="Elevating raw search into code intelligence: symbol call graphs and deep code prioritization",
        page_num=3,
        total_pages=4,
    )

    y = 715
    c.draw_text(40, y, "Stage 3: Structural Graph Expansion (RelationshipExpander)", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16
    s3_text = (
        "Isolated code snippets lack context. A controller calling an un-imported service is useless without knowing how "
        "that service is implemented. Unotusk executes a Breadth-First Search (BFS) over the code_dependencies table to "
        "gather related modules:"
    )
    y = c.draw_wrapped_text(40, y, s3_text, width=515, font="/F1", size=9, line_height=13, color=(0.25, 0.25, 0.25))

    y -= 8
    # Graph Expansion Diagram / Callout Box
    c.set_color_rgb(0.97, 0.98, 0.96, fill=True)
    c.rect(40, y - 72, 515, 72, fill=True, stroke=False)
    c.set_color_rgb(0.82, 0.88, 0.82, fill=False)
    c.rect(40, y - 72, 515, 72, fill=False, stroke=True)

    c.draw_text(50, y - 16, "1-Hop Inbound (Callers):", font="/F2", size=8.5, color=(0.15, 0.35, 0.15))
    c.draw_text(190, y - 16, "Discovers who calls this symbol (e.g. routes/checkout.py calls PaymentGateway)", font="/F1", size=8, color=(0.3, 0.3, 0.3))
    c.draw_text(50, y - 32, "1-Hop Outbound (Callees):", font="/F2", size=8.5, color=(0.15, 0.35, 0.15))
    c.draw_text(190, y - 32, "Discovers what this symbol depends on (e.g. PaymentGateway calls StripeSDK)", font="/F1", size=8, color=(0.3, 0.3, 0.3))
    c.draw_text(50, y - 48, "Type Definitions:", font="/F2", size=8.5, color=(0.15, 0.15, 0.15))
    c.draw_text(190, y - 48, "Pulls parameter types and return schemas (e.g. PaymentIntent, ChargeResult)", font="/F1", size=8, color=(0.3, 0.3, 0.3))
    c.draw_text(50, y - 64, "Hop Attenuation Factor:", font="/F2", size=8.5, color=(0.15, 0.35, 0.15))
    c.draw_text(190, y - 64, "1-Hop relevance = 0.85x; 2-Hop relevance = 0.60x to prevent graph explosion.", font="/F3", size=8, color=(0.4, 0.4, 0.4))

    y -= 90
    c.draw_text(40, y, "Stage 4: MultiSignalRanker & Anti-README Bias Engine", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16
    s4_text = (
        "Standard RAG models frequently fail developers by returning generic README.md files because documentation has high "
        "lexical overlap with user questions. Unotusk solves this with an explicit MultiSignalRanker scoring formula:"
    )
    y = c.draw_wrapped_text(40, y, s4_text, width=515, font="/F1", size=9, line_height=13, color=(0.25, 0.25, 0.25))

    y -= 12
    # Mathematical Formula Box
    c.set_color_rgb(0.96, 0.94, 0.92, fill=True)
    c.rect(40, y - 44, 515, 44, fill=True, stroke=False)
    c.set_color_rgb(0.9, 0.75, 0.65, fill=False)
    c.rect(40, y - 44, 515, 44, fill=False, stroke=True)

    c.draw_text(55, y - 18, "Final Score = ( S_lexical * W_lex + S_vector * W_vec + S_symbol * W_sym ) * M_boost * M_demote", font="/F5", size=8.5, color=(0.6, 0.25, 0.05))
    c.draw_text(55, y - 34, "Where weights are dynamically calibrated per query intent (e.g. symbol queries weight W_sym = 0.50).", font="/F3", size=7.5, color=(0.4, 0.4, 0.4))

    y -= 58
    c.draw_text(40, y, "The Four Precision Multipliers:", font="/F2", size=10, color=(0.15, 0.15, 0.15))
    y -= 14

    multipliers = [
        ("AST Code Definition Boost (1.8x):", "Chunks containing actual class, function, method, interface, or struct definitions receive an immediate 1.8x boost, prioritizing implementation code over comments."),
        ("Markdown / README Demotion (0.4x):", "Any .md, .rst, README, or docs/ chunk is penalized by 0.4x for implementation queries, eliminating superficial documentation matches."),
        ("Exact Symbol Match Boost (2.0x):", "When a chunk contains the exact queried symbol name (e.g. class PaymentService), its relevance score is doubled."),
        ("Test / Mock Demotion (0.7x):", "Files in tests/, test/, or mock directories receive a 0.7x dampener unless the user explicitly requested test coverage information.")
    ]

    for m_title, m_desc in multipliers:
        c.draw_text(45, y, m_title, font="/F2", size=8.5, color=(0.12, 0.12, 0.12))
        y = c.draw_wrapped_text(60, y - 11, m_desc, width=490, font="/F1", size=8, line_height=11.5, color=(0.32, 0.32, 0.32))
        y -= 4

    # =========================================================================
    # PAGE 4: STAGES 5 & 6 — CONTEXT ASSEMBLY & CONCRETE TRACE
    # =========================================================================
    c.new_page()
    draw_page_chrome(
        c,
        page_title="4. Context Assembly, Synthesis & Concrete Trace",
        subtitle="Token budgeting, grounded LLM synthesis, citation verification, and a live end-to-end trace",
        page_num=4,
        total_pages=4,
    )

    y = 715
    c.draw_text(40, y, "Stage 5 & 6: Context Assembly, Budgeting & LLM Grounding", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16
    s5_text = (
        "The ContextAssembler merges ranked code chunks, architectural skeletons, and team knowledge under a strict 6,000 "
        "token ceiling before passing the payload to the LLM Synthesizer (Groq Qwen/Llama or Claude 3.5 Sonnet)."
    )
    y = c.draw_wrapped_text(40, y, s5_text, width=515, font="/F1", size=9, line_height=13, color=(0.25, 0.25, 0.25))

    y -= 10
    # Token Budget Tier Table
    c.set_color_rgb(0.2, 0.22, 0.26, fill=True)
    c.rect(40, y - 18, 515, 18, fill=True, stroke=False)
    c.draw_text(48, y - 13, "Context Layer", font="/F2", size=8, color=(1, 1, 1))
    c.draw_text(160, y - 13, "Source Provider", font="/F2", size=8, color=(1, 1, 1))
    c.draw_text(290, y - 13, "Token Budget", font="/F2", size=8, color=(1, 1, 1))
    c.draw_text(390, y - 13, "Role in Answer Synthesis", font="/F2", size=8, color=(1, 1, 1))

    c_layers = [
        ("Repository Skeleton", "RepositorySkeletonBuilder", "~800 tokens", "Macro topology, directory tree, major subsystems"),
        ("Ranked Code Evidence", "MultiSignalRanker (Top 5-10)", "~3,800 tokens", "Exact function implementations & AST symbols"),
        ("Team ADRs & Rules", "KnowledgeRetriever", "~600 tokens", "Architectural constraints & team conventions"),
        ("Conversation History", "Message Repository", "~800 tokens", "Previous user questions and assistant answers")
    ]
    ry = y - 18
    for idx, (layer, prov, budget, role) in enumerate(c_layers):
        bg = (0.97, 0.97, 0.98) if idx % 2 == 0 else (1.0, 1.0, 1.0)
        c.set_color_rgb(*bg, fill=True)
        c.rect(40, ry - 18, 515, 18, fill=True, stroke=False)
        c.set_color_rgb(0.88, 0.88, 0.9, fill=False)
        c.line(40, ry - 18, 555, ry - 18)

        c.draw_text(48, ry - 13, layer, font="/F2", size=7.5, color=(0.15, 0.15, 0.15))
        c.draw_text(160, ry - 13, prov, font="/F1", size=7.5, color=(0.3, 0.3, 0.3))
        c.draw_text(290, ry - 13, budget, font="/F4", size=7.5, color=(0.1, 0.3, 0.6))
        c.draw_text(390, ry - 13, role, font="/F3", size=7.5, color=(0.35, 0.35, 0.35))
        ry -= 18

    y = ry - 20
    # Live Concrete Example Walkthrough
    c.draw_text(40, y, "End-to-End Concrete Trace: Real Query Execution", font="/F2", size=12, color=(0.85, 0.45, 0.15))
    y -= 16

    trace_box = (
        "USER QUERY: 'How does the payment webhook handle duplicate event delivery on branch features?'\n\n"
        "[1. ROUTING]       POST /api/v1/projects/proj-101/ask | branch='features' | user_id=usr-dev\n"
        "[2. DECOMPOSE]     Target symbols: ['WebhookHandler', 'handle_event'] | Keywords: ['payment', 'duplicate']\n"
        "[3. SNAPSHOT]      Resolved snapshot: snap-features-v4 (Branch: 'features', Commit: 7a8f9c2)\n"
        "[4. DB RETRIEVAL]  Found 38 candidates in code_chunks (pgvector) + 4 AST symbol matches in code_symbols\n"
        "[5. EXPANSION]     RelationshipExpander pulled 1-hop callee: IdempotencyKeyStore (src/billing/keys.py)\n"
        "[6. RANKER]        src/billing/webhook.py::handle_event: Score 4.82 (Boosted: AST Method 1.8x, Exact Sym 2.0x)\n"
        "                   docs/README.md: Score 0.41 (Demoted: Markdown 0.4x penalty applied)\n"
        "[7. SYNTHESIS]     Groq Qwen3.8-27b synthesizes grounded answer citing src/billing/webhook.py#L45-L78\n"
        "[8. VERIFICATION]  Citation gate validates lines 45-78 exist in snap-features-v4. Verified: 100% Grounded."
    )

    c.set_color_rgb(0.95, 0.96, 0.97, fill=True)
    c.rect(40, y - 145, 515, 145, fill=True, stroke=False)
    c.set_color_rgb(0.78, 0.82, 0.88, fill=False)
    c.rect(40, y - 145, 515, 145, fill=False, stroke=True)

    ty = y - 14
    for line in trace_box.split("\n"):
        if line.startswith("USER QUERY:"):
            c.draw_text(50, ty, line, font="/F5", size=8, color=(0.7, 0.25, 0.05))
        elif line.startswith("["):
            c.draw_text(50, ty, line[:18], font="/F5", size=7.5, color=(0.1, 0.35, 0.65))
            c.draw_text(160, ty, line[18:], font="/F4", size=7.5, color=(0.2, 0.22, 0.25))
        else:
            c.draw_text(50, ty, line, font="/F4", size=7.5, color=(0.3, 0.3, 0.3))
        ty -= 12.5

    # Save to disk
    c.save(output_path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/query_processing_lifecycle.pdf"
    generate_query_processing_pdf(out)
