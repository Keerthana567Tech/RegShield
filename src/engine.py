"""Master evaluation engine and safety score calculator for RegShield."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from .config import TESTS_FILE, REPORTS_DIR, CATEGORIES
from .database import CustomerDatabase
from .llm_client import LLMClient
from .evaluators import (
    BaseEvaluator,
    EvaluationResult,
    JailbreakEvaluator,
    PIIEvaluator,
    DataLeakageEvaluator,
    ToxicityEvaluator
)


class EvaluationEngine:
    """Coordinates risk evaluators, runs safety benchmarks, and computes safety scores."""

    def __init__(self, llm_client: Optional[LLMClient] = None, db: Optional[CustomerDatabase] = None):
        self.db = db or CustomerDatabase()
        self.llm = llm_client or LLMClient()
        self.jailbreak_eval = JailbreakEvaluator()
        self.pii_eval = PIIEvaluator(self.db)
        self.data_leak_eval = DataLeakageEvaluator(self.db)
        self.toxicity_eval = ToxicityEvaluator()

        self.evaluators: Dict[str, BaseEvaluator] = {
            "Jailbreak Resistance": self.jailbreak_eval,
            "PII Leakage": self.pii_eval,
            "Unauthorized Database Disclosure": self.data_leak_eval,
            "Toxicity/Bias": self.toxicity_eval
        }

    def infer_category(self, prompt: str) -> str:
        """Infers the most likely risk category for an ad-hoc user prompt."""
        p_lower = prompt.lower()
        if any(w in p_lower for w in ["database", "select *", "customers.json", "dump", "export all", "table"]):
            return "Unauthorized Database Disclosure"
        if any(w in p_lower for w in ["email", "phone", "contact", "address", "ssn", "mobile", "rahul", "priya", "amit"]):
            return "PII Leakage"
        if any(w in p_lower for w in ["insult", "kill", "hate", "racist", "ugly", "moron", "slur", "unfit"]):
            return "Toxicity/Bias"
        if any(w in p_lower for w in ["ignore", "dan", "developer mode", "evilbot", "override", "bypass"]):
            return "Jailbreak Resistance"
        return "Jailbreak Resistance"

    def evaluate_response(
        self,
        prompt: str,
        response: str,
        expected_category: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluates an LLM response against all safety criteria, prioritizing the target category.
        """
        category = expected_category or self.infer_category(prompt)

        # 1. Run the category-specific primary evaluator
        primary_evaluator = self.evaluators.get(category, self.jailbreak_eval)
        primary_result = primary_evaluator.evaluate(prompt, response, expected_category=category)

        # If the primary test failed, report the primary risk category
        if not primary_result.passed:
            return primary_result

        # 2. If primary passed, check if other severe risks were triggered
        if category != "Unauthorized Database Disclosure":
            db_res = self.data_leak_eval.evaluate(prompt, response)
            if not db_res.passed:
                return db_res

        if category != "PII Leakage":
            pii_res = self.pii_eval.evaluate(prompt, response)
            if not pii_res.passed:
                return pii_res

        if category != "Toxicity/Bias":
            tox_res = self.toxicity_eval.evaluate(prompt, response)
            if not tox_res.passed:
                return tox_res

        return primary_result

    def run_prompt(self, prompt: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Runs a single prompt through LLM and evaluates the outcome."""
        response = self.llm.generate(prompt)
        eval_result = self.evaluate_response(prompt, response, expected_category=category)
        return {
            "prompt": prompt,
            "response": response,
            "category": eval_result.category,
            "passed": eval_result.passed,
            "result": "PASS" if eval_result.passed else "FAIL",
            "reason": eval_result.reason,
            "evidence": eval_result.evidence,
            "score": eval_result.score
        }

    def load_predefined_tests(self) -> List[Dict[str, Any]]:
        """Loads test cases from the tests.json dataset."""
        if not TESTS_FILE.exists():
            return []
        with open(TESTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_predefined_tests(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        callback: Optional[Callable[[int, int, Dict[str, Any], str, EvaluationResult], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes predefined test cases, computes safety metrics, and logs the report.
        """
        all_tests = self.load_predefined_tests()
        if category:
            all_tests = [t for t in all_tests if t.get("category", "").lower() == category.lower()]
        if limit:
            all_tests = all_tests[:limit]

        total_tests = len(all_tests)
        results = []
        passed_count = 0

        # Category level counters
        cat_stats = {
            cat: {"total": 0, "passed": 0, "failed": 0}
            for cat in CATEGORIES
        }

        for idx, test in enumerate(all_tests, 1):
            test_prompt = test["prompt"]
            test_cat = test["category"]

            # Generate LLM response
            response = self.llm.generate(test_prompt)

            # Evaluate response
            eval_res = self.evaluate_response(test_prompt, response, expected_category=test_cat)

            if eval_res.passed:
                passed_count += 1

            # Update category stats
            if test_cat not in cat_stats:
                cat_stats[test_cat] = {"total": 0, "passed": 0, "failed": 0}
            cat_stats[test_cat]["total"] += 1
            if eval_res.passed:
                cat_stats[test_cat]["passed"] += 1
            else:
                cat_stats[test_cat]["failed"] += 1

            test_record = {
                "test_id": test.get("id", f"TEST-{idx:03d}"),
                "category": test_cat,
                "prompt": test_prompt,
                "response": response,
                "result": "PASS" if eval_res.passed else "FAIL",
                "passed": eval_res.passed,
                "reason": eval_res.reason,
                "evidence": eval_res.evidence
            }
            results.append(test_record)

            if callback:
                callback(idx, total_tests, test, response, eval_res)

        failed_count = total_tests - passed_count
        safety_score = (passed_count / total_tests * 100.0) if total_tests > 0 else 0.0

        summary = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "llm_mode": self.llm.mode,
            "model_name": self.llm.model_name if self.llm.mode == "gemini" else f"Simulated ({self.llm.mode})",
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "safety_score": round(safety_score, 1),
            "category_breakdown": {
                cat: {
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "score": round((stats["passed"] / stats["total"] * 100.0), 1) if stats["total"] > 0 else 0.0
                }
                for cat, stats in cat_stats.items() if stats["total"] > 0
            },
            "results": results
        }

        # Persist report
        self.save_report(summary)
        return summary

    def save_report(self, summary: Dict[str, Any]) -> Path:
        """Saves evaluation summary to a timestamped JSON file and optional CSV report."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = REPORTS_DIR / f"report_{timestamp_str}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Optional pandas export
        try:
            import pandas as pd
            if summary.get("results"):
                df = pd.DataFrame(summary["results"])
                csv_file = REPORTS_DIR / f"report_{timestamp_str}.csv"
                df.to_csv(csv_file, index=False)
        except Exception:
            pass

        return report_file

    def get_previous_reports(self) -> List[Dict[str, Any]]:
        """Retrieves past evaluation reports sorted by newest first."""
        report_files = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
        reports = []
        for file in report_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["file_name"] = file.name
                    reports.append(data)
            except Exception:
                continue
        return reports
