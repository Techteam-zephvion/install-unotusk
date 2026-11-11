"""
E1 Benchmarking Harness (Stage 2): Fair M0 (ATOM) vs M1 (Generative IE) vs M2 (Constrained Decoding).
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.
"""

import asyncio
import json
import logging
import statistics
from dataclasses import asdict, dataclass, field

from experiments.e1_generative_ie.data.dataset import E1TestCase, load_e1_dataset
from experiments.e1_generative_ie.extractor import E1Extractor
from experiments.e1_generative_ie.schema import E1ExtractionResult, ValidationStatus

logger = logging.getLogger("e1-benchmark")


@dataclass
class MetricSummary:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


@dataclass
class StratifiedCapabilityMetrics:
    """Evaluates capabilities split into Syntactic (ATOM-supported) vs Semantic (ATOM-unsupported)."""
    overall_f1: float = 0.0
    syntactic_supported_f1: float = 0.0
    semantic_unsupported_f1: float = 0.0


@dataclass
class ModelBenchmarkResult:
    model_name: str
    total_cases: int = 0
    annotation_classification: str = "PROVISIONAL_AI_DRAFT"
    live_model_status: str = "LIVE"
    entity_metrics: MetricSummary = field(default_factory=MetricSummary)
    relation_metrics: MetricSummary = field(default_factory=MetricSummary)
    event_metrics: MetricSummary = field(default_factory=MetricSummary)
    # Stratified fairness metrics
    entity_fairness: StratifiedCapabilityMetrics = field(default_factory=StratifiedCapabilityMetrics)
    relation_fairness: StratifiedCapabilityMetrics = field(default_factory=StratifiedCapabilityMetrics)
    schema_validity_rate: float = 1.0
    evidence_grounding_accuracy: float = 1.0
    unsupported_fact_rate: float = 0.0
    duplicate_extraction_rate: float = 0.0
    temporal_accuracy_rate: float = 1.0
    abstention_accuracy: float = 1.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)
    category_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)


class E1BenchmarkRunner:
    """Executes comparative evaluation across M0, M1, and M2 with fairness stratification."""

    def __init__(self, extractor: E1Extractor | None = None):
        self.extractor = extractor or E1Extractor()
        self.cases = load_e1_dataset()

    async def run_benchmark(self, split: str | None = None) -> dict[str, ModelBenchmarkResult]:
        """Runs evaluation over the dataset split ('dev', 'eval', or None for all 40)."""
        target_cases = [c for c in self.cases if split is None or c.split == split]

        results = {
            "M0_ATOM_Baseline": await self._evaluate_model("M0", target_cases),
            "M1_Generative_IE": await self._evaluate_model("M1", target_cases),
            "M2_Constrained_Decoding": await self._evaluate_model("M2", target_cases),
        }

        return results

    async def _evaluate_model(
        self,
        mode: str,
        cases: list[E1TestCase],
    ) -> ModelBenchmarkResult:
        model_label = (
            "Configuration M2 (Post-Gen Schema FSM Gating)"
            if mode == "M2"
            else f"Configuration {mode}"
        )
        res = ModelBenchmarkResult(
            model_name=model_label,
            total_cases=len(cases),
            live_model_status="LIVE" if self.extractor.live_llm_available else "BLOCKED_OFFLINE_PATH",
            annotation_classification="PROVISIONAL_AI_DRAFT (Human Review Pending)",
        )

        ent_tp, ent_fp, ent_fn = 0, 0, 0
        rel_tp, rel_fp, rel_fn = 0, 0, 0
        evt_tp, evt_fp, evt_fn = 0, 0, 0

        # Stratified trackers
        syn_ent_tp, syn_ent_fn = 0, 0
        sem_ent_tp, sem_ent_fn = 0, 0

        syn_rel_tp, syn_rel_fn = 0, 0
        sem_rel_tp, sem_rel_fn = 0, 0

        total_extracted_facts = 0
        total_grounded_facts = 0
        total_unsupported_facts = 0
        schema_valid_count = 0
        abstention_correct = 0

        cat_results: dict[str, dict[str, list[float]]] = {}

        for tc in cases:
            if tc.category not in cat_results:
                cat_results[tc.category] = {"ent_f1": [], "rel_f1": [], "evt_f1": []}

            # Run extraction
            if mode == "M0":
                extraction = self.extractor.extract_m0_atom_baseline(tc.commit)
            elif mode == "M1":
                extraction = await self.extractor.extract_m1_generative_ie(tc.commit)
            else:
                extraction = await self.extractor.extract_m2_constrained_decoding(tc.commit)

            res.latencies.append(extraction.latency_ms)

            # Check schema validity
            if isinstance(extraction, E1ExtractionResult):
                schema_valid_count += 1

            # Check abstention
            if tc.is_trivial:
                if extraction.abstention_triggered:
                    abstention_correct += 1
            else:
                if not extraction.abstention_triggered:
                    abstention_correct += 1

            # ---------------------------------------------------------
            # Evaluate Entities
            # ---------------------------------------------------------
            pred_entities = {e.entity_name.lower(): e for e in extraction.entities}
            exp_entities = {e.name.lower(): e for e in tc.expected_entities}

            cur_ent_tp = len(pred_entities.keys() & exp_entities.keys())
            cur_ent_fp = len(pred_entities.keys() - exp_entities.keys())
            cur_ent_fn = len(exp_entities.keys() - pred_entities.keys())
            ent_tp += cur_ent_tp
            ent_fp += cur_ent_fp
            ent_fn += cur_ent_fn

            ent_p = cur_ent_tp / (cur_ent_tp + cur_ent_fp) if (cur_ent_tp + cur_ent_fp) > 0 else (1.0 if not exp_entities else 0.0)
            ent_r = cur_ent_tp / (cur_ent_tp + cur_ent_fn) if (cur_ent_tp + cur_ent_fn) > 0 else (1.0 if not exp_entities else 0.0)
            ent_f1 = 2 * ent_p * ent_r / (ent_p + ent_r) if (ent_p + ent_r) > 0 else (1.0 if not exp_entities and not pred_entities else 0.0)
            cat_results[tc.category]["ent_f1"].append(ent_f1)

            # Stratified Entity evaluation
            syn_exp_entities = {e.name.lower(): e for e in tc.expected_entities if e.is_supported_by_atom}
            sem_exp_entities = {e.name.lower(): e for e in tc.expected_entities if not e.is_supported_by_atom}

            syn_ent_tp += len(pred_entities.keys() & syn_exp_entities.keys())
            syn_ent_fn += len(syn_exp_entities.keys() - pred_entities.keys())
            sem_ent_tp += len(pred_entities.keys() & sem_exp_entities.keys())
            sem_ent_fn += len(sem_exp_entities.keys() - pred_entities.keys())

            # ---------------------------------------------------------
            # Evaluate Relations
            # ---------------------------------------------------------
            pred_rels = {(r.subject.lower(), r.relation_type.lower(), r.object.lower()) for r in extraction.relations}
            exp_rels = {(r.subject.lower(), r.rel.lower(), r.obj.lower()) for r in tc.expected_relations}

            cur_rel_tp = len(pred_rels & exp_rels)
            cur_rel_fp = len(pred_rels - exp_rels)
            cur_rel_fn = len(exp_rels - pred_rels)
            rel_tp += cur_rel_tp
            rel_fp += cur_rel_fp
            rel_fn += cur_rel_fn

            rel_p = cur_rel_tp / (cur_rel_tp + cur_rel_fp) if (cur_rel_tp + cur_rel_fp) > 0 else (1.0 if not exp_rels else 0.0)
            rel_r = cur_rel_tp / (cur_rel_tp + cur_rel_fn) if (cur_rel_tp + cur_rel_fn) > 0 else (1.0 if not exp_rels else 0.0)
            rel_f1 = 2 * rel_p * rel_r / (rel_p + rel_r) if (rel_p + rel_r) > 0 else (1.0 if not exp_rels and not pred_rels else 0.0)
            cat_results[tc.category]["rel_f1"].append(rel_f1)

            # Stratified Relation evaluation
            syn_exp_rels = {(r.subject.lower(), r.rel.lower(), r.obj.lower()) for r in tc.expected_relations if r.is_supported_by_atom}
            sem_exp_rels = {(r.subject.lower(), r.rel.lower(), r.obj.lower()) for r in tc.expected_relations if not r.is_supported_by_atom}

            syn_rel_tp += len(pred_rels & syn_exp_rels)
            syn_rel_fn += len(syn_exp_rels - pred_rels)
            sem_rel_tp += len(pred_rels & sem_exp_rels)
            sem_rel_fn += len(sem_exp_rels - pred_rels)

            # ---------------------------------------------------------
            # Evaluate Events
            # ---------------------------------------------------------
            pred_evts = {(e.event_type.lower(), e.target_component.lower()) for e in extraction.events}
            exp_evts = {(e.type.lower(), e.target.lower()) for e in tc.expected_events}

            cur_evt_tp = len(pred_evts & exp_evts)
            cur_evt_fp = len(pred_evts - exp_evts)
            cur_evt_fn = len(exp_evts - pred_evts)
            evt_tp += cur_evt_tp
            evt_fp += cur_evt_fp
            evt_fn += cur_evt_fn

            evt_p = cur_evt_tp / (cur_evt_tp + cur_evt_fp) if (cur_evt_tp + cur_evt_fp) > 0 else (1.0 if not exp_evts else 0.0)
            evt_r = cur_evt_tp / (cur_evt_tp + cur_evt_fn) if (cur_evt_tp + cur_evt_fn) > 0 else (1.0 if not exp_evts else 0.0)
            evt_f1 = 2 * evt_p * evt_r / (evt_p + evt_r) if (evt_p + evt_r) > 0 else (1.0 if not exp_evts and not pred_evts else 0.0)
            cat_results[tc.category]["evt_f1"].append(evt_f1)

            # Grounding statistics
            all_facts = len(extraction.entities) + len(extraction.relations) + len(extraction.events)
            total_extracted_facts += all_facts
            grounded_in_case = sum(1 for e in extraction.entities if e.validation_status == ValidationStatus.VALIDATED) + \
                               sum(1 for r in extraction.relations if r.validation_status == ValidationStatus.VALIDATED) + \
                               sum(1 for ev in extraction.events if ev.validation_status == ValidationStatus.VALIDATED)
            total_grounded_facts += grounded_in_case
            total_unsupported_facts += (all_facts - grounded_in_case)

        # Global Metric Summaries
        res.entity_metrics = self._calc_summary(ent_tp, ent_fp, ent_fn)
        res.relation_metrics = self._calc_summary(rel_tp, rel_fp, rel_fn)
        res.event_metrics = self._calc_summary(evt_tp, evt_fp, evt_fn)

        # Fairness Stratification Summaries
        syn_ent_p = syn_ent_tp / (syn_ent_tp + ent_fp) if (syn_ent_tp + ent_fp) > 0 else 0.0
        syn_ent_r = syn_ent_tp / (syn_ent_tp + syn_ent_fn) if (syn_ent_tp + syn_ent_fn) > 0 else 0.0
        syn_ent_f1 = 2 * syn_ent_p * syn_ent_r / (syn_ent_p + syn_ent_r) if (syn_ent_p + syn_ent_r) > 0 else 0.0

        sem_ent_p = sem_ent_tp / (sem_ent_tp + ent_fp) if (sem_ent_tp + ent_fp) > 0 else 0.0
        sem_ent_r = sem_ent_tp / (sem_ent_tp + sem_ent_fn) if (sem_ent_tp + sem_ent_fn) > 0 else 0.0
        sem_ent_f1 = 2 * sem_ent_p * sem_ent_r / (sem_ent_p + sem_ent_r) if (sem_ent_p + sem_ent_r) > 0 else 0.0

        res.entity_fairness = StratifiedCapabilityMetrics(
            overall_f1=res.entity_metrics.f1,
            syntactic_supported_f1=round(syn_ent_f1, 4),
            semantic_unsupported_f1=round(sem_ent_f1, 4),
        )

        syn_rel_p = syn_rel_tp / (syn_rel_tp + rel_fp) if (syn_rel_tp + rel_fp) > 0 else 0.0
        syn_rel_r = syn_rel_tp / (syn_rel_tp + syn_rel_fn) if (syn_rel_tp + syn_rel_fn) > 0 else 0.0
        syn_rel_f1 = 2 * syn_rel_p * syn_rel_r / (syn_rel_p + syn_rel_r) if (syn_rel_p + syn_rel_r) > 0 else 0.0

        sem_rel_p = sem_rel_tp / (sem_rel_tp + rel_fp) if (sem_rel_tp + rel_fp) > 0 else 0.0
        sem_rel_r = sem_rel_tp / (sem_rel_tp + sem_rel_fn) if (sem_rel_tp + sem_rel_fn) > 0 else 0.0
        sem_rel_f1 = 2 * sem_rel_p * sem_rel_r / (sem_rel_p + sem_rel_r) if (sem_rel_p + sem_rel_r) > 0 else 0.0

        res.relation_fairness = StratifiedCapabilityMetrics(
            overall_f1=res.relation_metrics.f1,
            syntactic_supported_f1=round(syn_rel_f1, 4),
            semantic_unsupported_f1=round(sem_rel_f1, 4),
        )

        res.schema_validity_rate = schema_valid_count / len(cases) if cases else 1.0
        res.evidence_grounding_accuracy = total_grounded_facts / total_extracted_facts if total_extracted_facts > 0 else 1.0
        res.unsupported_fact_rate = total_unsupported_facts / total_extracted_facts if total_extracted_facts > 0 else 0.0
        res.abstention_accuracy = abstention_correct / len(cases) if cases else 1.0

        if res.latencies:
            sorted_lat = sorted(res.latencies)
            res.p50_latency_ms = statistics.median(sorted_lat)
            p95_idx = int(len(sorted_lat) * 0.95)
            res.p95_latency_ms = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]

        # Category Breakdown
        for cat, data in cat_results.items():
            res.category_breakdown[cat] = {
                "entity_f1": statistics.mean(data["ent_f1"]) if data["ent_f1"] else 0.0,
                "relation_f1": statistics.mean(data["rel_f1"]) if data["rel_f1"] else 0.0,
                "event_f1": statistics.mean(data["evt_f1"]) if data["evt_f1"] else 0.0,
            }

        return res

    def _calc_summary(self, tp: int, fp: int, fn: int) -> MetricSummary:
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return MetricSummary(
            precision=round(p, 4),
            recall=round(r, 4),
            f1=round(f1, 4),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
        )


async def main():
    from experiments.e1_generative_ie.constrained_decoding import (
        evaluate_structured_generation_comparison,
    )

    runner = E1BenchmarkRunner()
    print("Running E1 Benchmark across 40 scenarios...")
    bench_results = await runner.run_benchmark()
    serializable = {}
    for name, br in bench_results.items():
        serializable[name] = asdict(br)
        print(f"\n=================== {name} ({br.live_model_status}) ===================")
        print(f"Annotation Status: {br.annotation_classification}")
        print(f"Entities (Overall):   P={br.entity_metrics.precision:.4f}, R={br.entity_metrics.recall:.4f}, F1={br.entity_metrics.f1:.4f}")
        print(f"Entities (Syntactic): Supported F1={br.entity_fairness.syntactic_supported_f1:.4f}")
        print(f"Relations (Overall):  P={br.relation_metrics.precision:.4f}, R={br.relation_metrics.recall:.4f}, F1={br.relation_metrics.f1:.4f}")
        print(f"Relations (Syntactic): Supported F1={br.relation_fairness.syntactic_supported_f1:.4f}")
        print(f"Events (Overall):     P={br.event_metrics.precision:.4f}, R={br.event_metrics.recall:.4f}, F1={br.event_metrics.f1:.4f}")
        print(f"Schema Validity: {br.schema_validity_rate * 100:.1f}%, Grounding Acc: {br.evidence_grounding_accuracy * 100:.1f}%")
        print(f"P50 Latency: {br.p50_latency_ms:.2f}ms, P95 Latency: {br.p95_latency_ms:.2f}ms")

    # Evaluate structured generation mechanism overhead
    sample_payloads = [
        '{"entities": [{"entity_name": "Calculator", "entity_type": "CLASS", "file_path": "calc.py"}]}',
        '```json\n{"entities": [{"entity_name": "APIClient", "entity_type": "SERVICE", "file_path": "client.py"}]}\n```',
        '{"entities": [{"entity_name": "BadEnt"}]}',  # missing file_path
    ]
    struct_metrics = evaluate_structured_generation_comparison(sample_payloads)
    serializable["_structured_generation_comparison"] = {k: asdict(v) for k, v in struct_metrics.items()}

    out_paths = [
        "docs/reports/information_extraction/e1_stage2_benchmark_results.json",
        "docs/reports/information_extraction/e1_benchmark_results.json",
    ]
    for out_path in out_paths:
        with open(out_path, "w") as f:
            json.dump(serializable, f, indent=2)
        print(f"Exported benchmark results to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
