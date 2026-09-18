"""RegShield — Automated AI Safety & Risk Evaluation Tool.
Main application entry point.
"""

import sys
import argparse
from src.config import CATEGORIES
from src.engine import EvaluationEngine
from src.llm_client import LLMClient
from src.console import ConsoleApp


def parse_args():
    parser = argparse.ArgumentParser(
        description="RegShield: Automated AI Safety & Risk Evaluation Tool"
    )
    parser.add_argument(
        "--mode",
        choices=["gemini", "simulated_safe", "simulated_vulnerable"],
        help="LLM execution mode: 'gemini', 'simulated_safe', or 'simulated_vulnerable'"
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all predefined safety tests and print summary"
    )
    parser.add_argument(
        "--category",
        choices=CATEGORIES,
        help="Filter predefined tests by risk category"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of predefined tests to run"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Evaluate a single prompt directly via command line"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    llm = LLMClient()
    if args.mode:
        llm.set_mode(args.mode)

    engine = EvaluationEngine(llm_client=llm)

    # Direct single prompt evaluation mode
    if args.prompt:
        print(f"\nEvaluating prompt: '{args.prompt}'")
        res = engine.run_prompt(args.prompt)
        print("\n" + "=" * 40)
        print(f"LLM Response:\n{res['response']}")
        print("=" * 40)
        print(f"Category : {res['category']}")
        print(f"Result   : {res['result']}")
        print(f"Reason   : {res['reason']}")
        if res['evidence']:
            print(f"Evidence : {', '.join(res['evidence'])}")
        print("=" * 40 + "\n")
        return

    # Headless batch test runner mode
    if args.run_all or args.category or args.limit:
        print(f"\nRunning Predefined Safety Benchmark (Mode: {llm.mode})...\n")
        app = ConsoleApp(engine=engine)

        def simple_callback(idx, total, test, resp, eval_res):
            status = "PASS" if eval_res.passed else "FAIL"
            print(f"[{idx}/{total}] [{status}] ({test['category']}) - {test['prompt'][:60]}...")

        summary = engine.run_predefined_tests(
            category=args.category,
            limit=args.limit,
            callback=simple_callback
        )
        print()
        app.display_test_summary(summary)
        return

    # Default: Interactive Console Application
    app = ConsoleApp(engine=engine)
    app.run()


if __name__ == "__main__":
    main()
