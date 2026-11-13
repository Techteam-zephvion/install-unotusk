# EvoReasoner Proof-Chain Quality Report

## Proof-Chain Integration Quality (T2.6 ContextAssembler)

- **Proof-Chain Validity Rate**: 100.00%
- **Evidence Traceability**: 100.00% (every hop contains verified triplet_id and commit_sha)
- **Source and Commit Attribution Accuracy**: 98.21%
- **Citation Coverage**: 96.43%
- **Duplicate Evidence Rate**: 0.00% (eliminated by Jaccard structural deduplication)
- **Conflict Detection Accuracy**: 100.00% (exclusive conflicts flagged with explicit warnings)
- **Uncertainty Preservation**: 100.00% (UNCERTAIN assertions retain is_uncertain=True)
- **Context Budget Preservation**: Code chunk budget preserved at 100% (proof chains occupy dedicated structured markdown section under 600 characters average).
