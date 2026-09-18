"""Interactive Console Interface for RegShield AI Safety & Risk Evaluator."""

import os
import sys
import time
from typing import Optional

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_ENABLED = True
except ImportError:
    COLOR_ENABLED = False
    class Fore:
        GREEN = RED = CYAN = YELLOW = WHITE = BLUE = MAGENTA = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from .config import GEMINI_API_KEY, CATEGORIES
from .engine import EvaluationEngine
from .evaluators import EvaluationResult


def clear_screen():
    """Clears the console screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    """Prints the RegShield application banner."""
    print(f"{Fore.CYAN}{Style.BRIGHT}========================================")
    print("          REGSHIELD AI EVALUATOR        ")
    print(f"========================================{Style.RESET_ALL}")


class ConsoleApp:
    """Manages the interactive terminal UI and user workflows."""

    def __init__(self, engine: Optional[EvaluationEngine] = None):
        self.engine = engine or EvaluationEngine()

    def run(self):
        """Main application loop."""
        while True:
            self.display_main_menu()
            choice = input(f"{Fore.YELLOW}Enter your choice: {Style.RESET_ALL}").strip()

            if choice == "1":
                self.run_predefined_tests_flow()
            elif choice == "2":
                self.test_custom_prompt_flow()
            elif choice == "3":
                self.view_previous_results_flow()
            elif choice == "4":
                self.configure_settings_flow()
            elif choice == "5" or choice.lower() in ["exit", "quit", "q"]:
                print(f"\n{Fore.CYAN}Exiting RegShield. Stay safe!{Style.RESET_ALL}\n")
                break
            else:
                print(f"{Fore.RED}Invalid option. Please enter a number between 1 and 5.{Style.RESET_ALL}\n")
                time.sleep(1)

    def display_main_menu(self):
        """Renders the main selection menu."""
        print_banner()
        mode_str = self.engine.llm.mode.upper()
        if self.engine.llm.mode == "gemini":
            status_indicator = f"{Fore.GREEN}[Gemini API: {self.engine.llm.model_name}]{Style.RESET_ALL}"
        elif self.engine.llm.mode == "simulated_vulnerable":
            status_indicator = f"{Fore.RED}[Simulation: Vulnerable Mode (Demo Fails)]{Style.RESET_ALL}"
        else:
            status_indicator = f"{Fore.CYAN}[Simulation: Safe Mode]{Style.RESET_ALL}"

        print(f"Active Mode: {status_indicator}\n")
        print("1. Run predefined safety tests")
        print("2. Test your own prompt")
        print("3. View previous results")
        print("4. LLM & Model Settings")
        print("5. Exit\n")

    def test_custom_prompt_flow(self):
        """Interactive loop for testing custom user prompts."""
        print(f"\n{Fore.CYAN}========================================")
        print("         CUSTOM PROMPT EVALUATION       ")
        print(f"========================================{Style.RESET_ALL}")
        print("(Type 'back' or 'exit' to return to main menu)\n")

        while True:
            print(f"{Fore.YELLOW}Enter your prompt:{Style.RESET_ALL}")
            prompt = input("> ").strip()

            if not prompt:
                continue
            if prompt.lower() in ["back", "exit", "menu", "q"]:
                break

            print("\nQuerying LLM and evaluating response...")
            result_data = self.engine.run_prompt(prompt)

            # Display LLM Response
            print(f"\n{Fore.CYAN}----------------------------------------")
            print("LLM RESPONSE")
            print(f"----------------------------------------{Style.RESET_ALL}\n")
            for line in result_data["response"].split("\n"):
                print(f"> {line}")

            # Display Evaluation
            print(f"\n{Fore.CYAN}----------------------------------------")
            print("EVALUATION")
            print(f"----------------------------------------{Style.RESET_ALL}\n")

            print(f"Risk Category : {result_data['category']}")
            
            passed = result_data["passed"]
            res_color = Fore.GREEN if passed else Fore.RED
            res_text = f"{res_color}{Style.BRIGHT}{result_data['result']}{Style.RESET_ALL}"
            print(f"Result        : {res_text}")

            if passed:
                print(f"Reason        : {result_data['reason']}")
            else:
                print(f"\n{Fore.RED}Detected Risk:{Style.RESET_ALL}")
                print(f"{result_data['reason']}")
                if result_data["evidence"]:
                    print(f"\n{Fore.RED}Evidence:{Style.RESET_ALL}")
                    for ev in result_data["evidence"]:
                        print(f"- {ev}")

            print(f"\n{Fore.CYAN}----------------------------------------{Style.RESET_ALL}\n")

    def run_predefined_tests_flow(self):
        """Executes predefined tests with live progress and comprehensive final score."""
        print(f"\n{Fore.CYAN}========================================")
        print("       PREDEFINED SAFETY TESTS          ")
        print(f"========================================{Style.RESET_ALL}")

        print("Select test scope:")
        print("1. Run all predefined tests (Full Suite: 72 tests)")
        print("2. Quick benchmark (15 tests)")
        print("3. Filter by category")
        print("4. Back to main menu\n")

        choice = input(f"{Fore.YELLOW}Enter choice (1-4): {Style.RESET_ALL}").strip()
        if choice == "4" or choice.lower() in ["back", "q"]:
            return

        category_filter = None
        limit = None

        if choice == "1":
            limit = None
        elif choice == "2":
            limit = 15
        elif choice == "3":
            print("\nAvailable categories:")
            for i, cat in enumerate(CATEGORIES, 1):
                print(f"{i}. {cat}")
            cat_choice = input(f"{Fore.YELLOW}Select category (1-{len(CATEGORIES)}): {Style.RESET_ALL}").strip()
            try:
                cat_idx = int(cat_choice) - 1
                if 0 <= cat_idx < len(CATEGORIES):
                    category_filter = CATEGORIES[cat_idx]
                else:
                    print(f"{Fore.RED}Invalid category. Running all tests.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Running all tests.{Style.RESET_ALL}")
        else:
            limit = 15

        print(f"\n{Fore.CYAN}Starting evaluation...{Style.RESET_ALL}\n")

        def test_callback(idx: int, total: int, test_dict: dict, response: str, res: EvaluationResult):
            status_color = Fore.GREEN if res.passed else Fore.RED
            status_tag = f"{status_color}{Style.BRIGHT}{'PASS' if res.passed else 'FAIL'}{Style.RESET_ALL}"

            print(f"Running Test {idx}/{total}...")
            print(f"Category : {test_dict['category']}")
            prompt_snippet = test_dict['prompt'][:90] + ("..." if len(test_dict['prompt']) > 90 else "")
            print(f"Prompt   : {prompt_snippet}")
            print("\nLLM Response:")
            resp_snippet = response.strip()[:140].replace("\n", " ") + ("..." if len(response.strip()) > 140 else "")
            print(f"{resp_snippet}\n")
            print(f"Result   : {status_tag}")
            if not res.passed and res.evidence:
                ev_str = ", ".join(res.evidence[:2])
                print(f"Evidence : {Fore.RED}{ev_str}{Style.RESET_ALL}")
            print("-" * 40 + "\n")

        summary = self.engine.run_predefined_tests(
            category=category_filter,
            limit=limit,
            callback=test_callback
        )

        # Print Final Summary Banner
        self.display_test_summary(summary)
        input(f"{Fore.YELLOW}\nPress Enter to return to main menu...{Style.RESET_ALL}")

    def display_test_summary(self, summary: dict):
        """Displays the formatted final test summary matching user specification."""
        print(f"{Fore.CYAN}{Style.BRIGHT}========================================")
        print("          FINAL TEST SUMMARY            ")
        print(f"========================================{Style.RESET_ALL}\n")

        total = summary["total_tests"]
        passed = summary["passed"]
        failed = summary["failed"]
        score = summary["safety_score"]

        print(f"Total Tests : {total}")
        print(f"Passed      : {Fore.GREEN}{passed}{Style.RESET_ALL}")
        print(f"Failed      : {Fore.RED if failed > 0 else Fore.GREEN}{failed}{Style.RESET_ALL}\n")

        score_color = Fore.GREEN if score >= 80 else (Fore.YELLOW if score >= 60 else Fore.RED)
        print(f"Safety Score: {score_color}{Style.BRIGHT}{score}%{Style.RESET_ALL}\n")

        breakdown = summary.get("category_breakdown", {})
        for cat, stats in breakdown.items():
            cat_passed = stats["passed"]
            cat_total = stats["total"]
            cat_color = Fore.GREEN if cat_passed == cat_total else Fore.YELLOW
            # Left align category name
            print(f"{cat:<32} : {cat_color}{cat_passed}/{cat_total} Passed{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")
        print(f"Results report saved to: reports/ folder (JSON & CSV)")

    def view_previous_results_flow(self):
        """Displays historical evaluation runs."""
        reports = self.engine.get_previous_reports()
        print(f"\n{Fore.CYAN}========================================")
        print("         PREVIOUS EVALUATION RUNS       ")
        print(f"========================================{Style.RESET_ALL}\n")

        if not reports:
            print("No previous evaluation reports found in reports/ folder.")
            input(f"\n{Fore.YELLOW}Press Enter to return to main menu...{Style.RESET_ALL}")
            return

        for idx, rep in enumerate(reports[:10], 1):
            ts = rep.get("timestamp", "Unknown time")
            score = rep.get("safety_score", 0.0)
            total = rep.get("total_tests", 0)
            passed = rep.get("passed", 0)
            failed = rep.get("failed", 0)
            mode = rep.get("llm_mode", "Unknown")

            score_color = Fore.GREEN if score >= 80 else (Fore.YELLOW if score >= 60 else Fore.RED)
            print(f"[{idx}] {ts} | Mode: {mode}")
            print(f"    Total: {total} | Passed: {passed} | Failed: {failed} | Score: {score_color}{score}%{Style.RESET_ALL}")
            print("-" * 40)

        input(f"\n{Fore.YELLOW}Press Enter to return to main menu...{Style.RESET_ALL}")

    def configure_settings_flow(self):
        """Settings menu to configure Gemini API Key and switch simulation modes."""
        print(f"\n{Fore.CYAN}========================================")
        print("         SETTINGS & MODEL CONFIG        ")
        print(f"========================================{Style.RESET_ALL}\n")

        current_mode = self.engine.llm.mode
        api_key_masked = ("*" * (len(self.engine.llm.api_key) - 6) + self.engine.llm.api_key[-6:]) if len(self.engine.llm.api_key) > 6 else (self.engine.llm.api_key or "Not set")

        print(f"Current Mode    : {Fore.CYAN}{current_mode}{Style.RESET_ALL}")
        print(f"Gemini API Key  : {api_key_masked}")
        print(f"Gemini Model    : {self.engine.llm.model_name}\n")

        print("1. Switch to Live Gemini API Mode")
        print("2. Switch to Simulated Safe LLM Mode (Hardened Assistant)")
        print("3. Switch to Simulated Vulnerable LLM Mode (Demo FAIL Detection)")
        print("4. Enter/Update Gemini API Key")
        print("5. Back to Main Menu\n")

        choice = input(f"{Fore.YELLOW}Select an option (1-5): {Style.RESET_ALL}").strip()

        if choice == "1":
            if not self.engine.llm.api_key:
                print(f"\n{Fore.RED}No Gemini API key found. Please enter an API key first (Option 4).{Style.RESET_ALL}")
            else:
                try:
                    self.engine.llm.set_mode("gemini")
                    print(f"\n{Fore.GREEN}Switched to Live Gemini API mode.{Style.RESET_ALL}")
                except Exception as e:
                    print(f"\n{Fore.RED}Error initializing Gemini API: {e}{Style.RESET_ALL}")
        elif choice == "2":
            self.engine.llm.set_mode("simulated_safe")
            print(f"\n{Fore.GREEN}Switched to Simulated Safe mode.{Style.RESET_ALL}")
        elif choice == "3":
            self.engine.llm.set_mode("simulated_vulnerable")
            print(f"\n{Fore.YELLOW}Switched to Simulated Vulnerable mode (attacks will succeed to showcase FAIL detection).{Style.RESET_ALL}")
        elif choice == "4":
            new_key = input("\nEnter your Google Gemini API Key: ").strip()
            if new_key:
                self.engine.llm.set_api_key(new_key)
                print(f"{Fore.GREEN}API Key saved and Gemini mode activated!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}No key entered.{Style.RESET_ALL}")

        time.sleep(1)
