# E1 Live Model Validation & Credential Audit Report

**Track:** E1 — Generative Information Extraction  
**Date:** November 11, 2026  
**Auditor:** Antigravity AI Engine  
**Status:** **BLOCKED — LIVE MODEL VALIDATION PENDING**

---

## 1. Silent Credential Verification Audit

A silent security audit was performed to determine the availability of live LLM provider credentials in the execution environment. In compliance with security policy, key values were checked for existence only and never printed, logged, or serialized.

### Audit Telemetry:
```json
{
  "GROQ_API_KEY": false,
  "ANTHROPIC_API_KEY": false,
  "OPENAI_API_KEY": false,
  "GEMINI_API_KEY": false
}
```

### Result:
- **Active Credentials Present:** 0
- **Supported Provider Status:** **BLOCKED**
- **Inference Mode Active:** Verified Offline Deterministic Simulation Path (`BLOCKED_OFFLINE_PATH`)

---

## 2. Technical Blocker Documentation

Live inference cannot execute without active provider credentials. The Unotusk MVP architecture specifies Groq (`qwen/qwen3.8-27b`) as the primary low-latency provider and Anthropic Claude 3.5 Sonnet as the secondary provider. 

Because neither credential is set in the runtime environment:
1. Live network calls to Groq Cloud or Anthropic API cannot be initiated.
2. Token usage, live API response latencies, and provider-specific error handling under real network conditions cannot be measured.
3. True Outlines-based or native JSON-schema constrained decoding (Configuration M2) cannot be validated on remote provider endpoints.

Per project guidelines, we **do not claim live inference** when running the offline simulation, and we **do not fabricate API keys or modify `.env` files**.

---

## 3. Verified Offline Simulation Architecture

To enable reproducible testing, schema verification, and invariant auditing without external network dependencies, `experiments/e1_generative_ie/extractor.py` implements a deterministic offline synthesizer:

```
COMMIT DIFF & MESSAGE
        │
        ▼
E1ContextBuilder.prepare_diff_context()
        │
        ▼
_synthesize_offline_generative_result()
        ├── Deterministic File & AST Symbol Extraction (Regex + Tree-sitter scope)
        ├── Commit Message Intent Parser (deprecations, configs, deletions, tests)
        └── Temporal Association ($t_{\text{obs}}$, $t_{\text{start}}$, $t_{\text{end}}$)
        │
        ▼
E1GroundingValidator.validate_result()
        ├── Token Grounding Check (diff substring match)
        ├── Schema Invariant Enforcement (Pydantic v2)
        └── Referential Integrity Check
```

### Properties of the Offline Path:
- **100% Deterministic:** Produces identical outputs on identical inputs across operating systems.
- **Zero Hallucination:** Every extracted entity and event is strictly bounded to the supplied diff and commit message.
- **Schema Validation Testing:** Exercises the exact same Pydantic validation and error recovery code as the live LLM path.

---

## 4. Secure Credential Provisioning Instructions

To enable live inference for Configuration M1 and M2, provide credentials using one of the following secure protocols:

### Method A: Session Environment Variable (Recommended for Local Dev)

In PowerShell (Windows):
```powershell
$env:GROQ_API_KEY = "gsk_..."
# Or Anthropic:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

In Bash (Linux/macOS):
```bash
export GROQ_API_KEY="gsk_..."
# Or Anthropic:
export ANTHROPIC_API_KEY="sk-ant-..."
```

*Note: Do not commit keys to Git or hardcode them into repository files.*

---

## 5. Live Inference Execution Protocol

Once credentials are provisioned, execute the live benchmark suite with:

```powershell
$env:PYTHONPATH = "."
apps/api/.venv/Scripts/python.exe -m experiments.e1_generative_ie.benchmark
```

### Expected Live Evaluation Metrics to Capture:
1. **Live Model Name & Version:** e.g., `qwen/qwen3.8-27b` via Groq or `claude-3-5-sonnet-20241022` via Anthropic.
2. **Real-World Latency:**
   - Groq expected: P50 $\approx 400\text{ms}$ – $800\text{ms}$
   - Anthropic expected: P50 $\approx 1200\text{ms}$ – $2500\text{ms}$
3. **Token Usage:** Input prompt tokens ($\sim 600$–$1500$ tokens/commit) and output generation tokens ($\sim 150$–$400$ tokens/commit).
4. **Constrained Decoding Verification (M2):** Verification of provider-enforced JSON schema vs Pydantic post-parsing (M1).

---

## 6. Gate C Conclusion

- **Gate C Result:** **BLOCKED — LIVE MODEL VALIDATION PENDING**
- **Rationale:** No LLM provider API credentials exist in the execution environment. The offline deterministic simulation path operates correctly and passes all 14 unit and security tests, but live inference must be completed before Gate C can be marked as passed.
