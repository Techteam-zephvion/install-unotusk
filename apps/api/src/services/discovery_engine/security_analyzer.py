import re
from apps.api.src.models.enums import FindingCategory, FindingSeverity, FindingConfidence
from apps.api.src.services.discovery_engine.base import DiscoveryAnalyzer, CandidateFinding, DiscoveryContext

class SecurityAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.SECURITY_RISK

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings = []

        # 1. Hardcoded Secrets Detection
        secret_patterns = [
            (re.compile(r"(['\"])(?:api[_-]?key|secret|token|password|auth[_-]?token)\1\s*[:=]\s*(['\"])[a-zA-Z0-9_\-]{8,}\2", re.IGNORECASE), "Hardcoded Secret/Token"),
            (re.compile(r"['\"](ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{48}|gsk_[a-zA-Z0-9]{10,})['\"]"), "Hardcoded API Key (GitHub/OpenAI/Groq)")
        ]

        for chunk in ctx.chunks:
            if not chunk.content:
                continue
                
            for pattern, reason in secret_patterns:
                match = pattern.search(chunk.content)
                if match:
                    findings.append(
                        CandidateFinding(
                            category=self.category,
                            title="Hardcoded Secret Detected",
                            description=f"Found a potential hardcoded secret or token in `{chunk.name}`.",
                            why_it_matters="Hardcoding secrets in source code is a critical security vulnerability. If the repository is compromised or leaked, attackers can immediately pivot to external services.",
                            severity=FindingSeverity.CRITICAL,
                            confidence=FindingConfidence.HIGH,
                            recommendation="Move this secret to a secure environment variable or a secret manager (like AWS Secrets Manager or HashiCorp Vault) and rotate the compromised credential immediately.",
                            evidence=[{"file_path": chunk.path, "chunk_name": chunk.name, "line": chunk.start_line, "reason": reason}],
                            related_entities=[chunk.path],
                            score=9.5
                        )
                    )

        # 2. Insecure functions (eval, md5)
        insecure_symbols = {
            "eval": ("Usage of eval()", "eval() allows arbitrary code execution, which can lead to Remote Code Execution (RCE) if user input is passed to it.", FindingSeverity.CRITICAL),
            "md5": ("Insecure Hashing Algorithm (MD5)", "MD5 is cryptographically broken and vulnerable to collision attacks.", FindingSeverity.HIGH),
            "sha1": ("Insecure Hashing Algorithm (SHA1)", "SHA1 is weak and vulnerable to collision attacks.", FindingSeverity.MEDIUM),
        }

        for symbol in ctx.symbols:
            name_lower = symbol.name.lower()
            if name_lower in insecure_symbols:
                title, desc, sev = insecure_symbols[name_lower]
                
                file = ctx.file_by_id.get(symbol.file_id)
                path = file.path if file else "unknown"
                
                findings.append(
                    CandidateFinding(
                        category=self.category,
                        title=title,
                        description=f"Detected potentially dangerous function/symbol `{symbol.name}` in `{path}`.",
                        why_it_matters=desc,
                        severity=sev,
                        confidence=FindingConfidence.MEDIUM,
                        recommendation="Use a secure alternative (e.g., AST parsing instead of eval, SHA-256 or bcrypt instead of MD5/SHA1).",
                        evidence=[{"file_path": path, "symbol": symbol.name, "line": symbol.start_line}],
                        related_entities=[path],
                        score=7.0 if sev == FindingSeverity.HIGH else 8.5
                    )
                )

        return findings
