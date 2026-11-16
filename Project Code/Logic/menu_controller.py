from input_output_manager import (
    ask_yes_no,
    choose_cases,
    create_prompt,
    filter_input,
    input_manager,
    keyword_input,
    print_cases,
    print_output,
)
from Logic.ai_response import AIResponse


class MenuController:
    """Handles every menu option. Options are looked up in a dictionary of
    handler methods, so there is no if/elif chain per choice."""

    def __init__(self, engine, repository, user_profile=None):
        # ASSOCIATION: the controller collaborates with these objects (calls them)
        # but is not made of them and does not control their lifecycle.
        self._engine = engine
        self._repository = repository
        self._user_profile = user_profile  # the signed-in user
        self.__handlers = {
            "1": self._start_assessment,
            "2": self._list_cases,
            "3": self._search_records,
            "4": self._export_csv,
            "5": self._show_statistics,
            "6": self._exit,
        }

    @property
    def engine(self):
        return self._engine

    def handle(self, choice):
        """Run the chosen option. Returns True if the program should exit."""
        handler = self.__handlers.get(choice)
        if handler is None:
            print_output("Invalid menu option.")
            return False
        return handler() is True

    # ---- menu options (protected) ----------------------------------------

    def _start_assessment(self):
        patient_data = input_manager(self._user_profile)
        prompt = create_prompt(patient_data)

        # Pull the age out of the patient data so the AI can factor it in
        age = patient_data.get("age") if isinstance(patient_data, dict) else None

        result = self._engine.process(prompt, age)
        if result["ai_response"] is None:
            print_output(
                "\nUnable to complete the assessment "
                "because the AI service failed."
            )
            return

        self._engine.save_exchanges(result["exchanges"])
        print_output("\n=== Assessment Result ===")
        if result.get("is_health_related"):
            self._show_urgency_classification(result)
        if result.get("age_risk"):
            print_output(f"Age Risk: {result['age_risk']}")
        # Show the Next-Step Guidance section; if the reply has none (for example the
        # "not health-related" message), show the whole reply instead of printing None.
        guidance = AIResponse(result["ai_response"]).section("Next-Step Guidance:")
        print_output(guidance or result["ai_response"])
        if result.get("is_emergency"):
            self._show_emergency_service_guidance()
        self._show_guideline_check(
            result.get("validation"), is_emergency=result.get("is_emergency", False)
        )

    def _show_emergency_service_guidance(self):
        advice = self._engine.emergency_service_guidance()
        if not advice:
            return
        print_output("\n=== Emergency Advice (Singapore) ===")
        print_output(
            "If you are in Singapore, call 995 for a life-threatening emergency. "
            "If you are elsewhere, call your local emergency number."
        )
        for recommendation in advice["recommendations"]:
            print_output(f"- {recommendation}")
        if advice["source_url"]:
            print_output(f"Source: {advice['source_url']}")
        if advice["needs_review"]:
            print_output(
                "This service guidance is general information and does not replace "
                "instructions from emergency responders or medical professionals."
            )

    @staticmethod
    def _show_urgency_classification(result):
        """Print the urgency classification, with the AI's certainty when it gave one."""
        line = f"Urgency classification: {result['urgency_classification']}"
        if result.get("certainty"):
            line += f" - certainty {result['certainty']:.0%}"
        validation = result.get("validation")
        if validation and validation.get("escalated"):
            line += " - raised after the guideline check"
        print_output(line)

    @staticmethod
    def _show_guideline_check(validation, is_emergency=False):
        """Print concise sources for non-emergencies and findings for emergencies."""
        if not validation or not validation["findings"]:
            return
        print_output("\n=== Guideline Check ===")
        if validation.get("escalated"):
            print_output(
                f"Urgency raised from '{validation['urgency_before']}' to "
                f"'{validation['urgency_after']}' based on the guideline data below."
            )
        for finding in validation["findings"]:
            source_details = finding.get("source_details")
            if not is_emergency and source_details:
                source_url = source_details.get("source_url")
                citation = (
                    f"{source_details['id']} | {source_details['source_name']}"
                )
                if source_url:
                    citation += f" | {source_url}"
                print_output(f"- {citation}")
                continue
            source = f" [{finding['source']}]" if finding["source"] else ""
            print_output(f"- {finding['message']}{source}")
        if validation["needs_review"]:
            print_output(
                "Note: this guideline data is marked as needing professional review. "
                "The check supports, but does not replace, advice from a doctor."
            )

    def _list_cases(self):
        print_cases()

    def _search_records(self):
        keyword = keyword_input()
        results = self._repository.search(keyword)
        if not results:
            print_output(f"\nNo matching records found for '{keyword}'.")
        else:
            self._repository.show_history(results)

    def _export_csv(self):
        cases = self._repository.export_choices()

        # Zero or one case: nothing to choose, so export straight away
        # (with no records the exporter prints "No records to export yet.").
        if len(cases) <= 1:
            self._repository.export_csv()
            return

        case_ids = choose_cases(cases)
        if not case_ids:
            print_output("Export cancelled.")
            return

        self._repository.export_csv(case_ids)

    def _show_statistics(self):
        query = filter_input()
        try:
            self._repository.show_stats(query)
            if ask_yes_no("Show per-case breakdown? (y/n): "):
                self._repository.show_stats(query, per_case=True)
        except ValueError as exc:
            print_output(f"\n[Stats] {exc}")

    def _exit(self):
        return True
