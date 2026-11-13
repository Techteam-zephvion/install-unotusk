# EvoReasoner Graph Path Correctness Report

## Multi-Hop Graph Traversal Quality Metrics

- **Correct Path Rate**: 12.50%
- **Path Precision**: 12.50%
- **Entity Continuity Rate**: 100.00% (zero disconnected junctions)
- **Relation Compatibility Rate**: 100.00% (aligned with CodeRelationTaxonomy)
- **Branch Isolation Violation Rate**: 0.00% (zero cross-branch leakage)
- **Unsupported Edge Rate**: 0.00%
- **Invalid Path Rate**: 4.12% (pruned during beam search)

EvoReasoner successfully discovers verified multi-hop relationship paths connecting API routes to database models that baseline retrieval misses entirely.