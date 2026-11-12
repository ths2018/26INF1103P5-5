from input_output_manager import (
    create_prompt,
    input_manager,
    keyword_input,
    print_cases,
    print_output,
)
from Logic.ai_response import AIResponse


class MenuController:
    """Handles every menu option. Options are looked up in a dictionary of
    handler methods, so there is no if/elif chain per choice."""

    def __init__(self, engine, repository):
        # ASSOCIATION: the controller collaborates with these objects (calls them)
        # but is not made of them and does not control their lifecycle.
        self._engine = engine
        self._repository = repository
        self.__handlers = {
            "1": self._start_assessment,
            "2": self._list_cases,
            "3": self._search_records,
            "4": self._export_csv,
            "5": self._export_xlsx,
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
        patient_data = input_manager()
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
        if result.get("age_risk"):
            print_output(f"Age Risk: {result['age_risk']}")
        print_output(AIResponse(result["ai_response"]).section("Next-Step Guidance:"))

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
        self._repository.export_csv()

    def _export_xlsx(self):
        self._repository.export_xlsx_and_open()

    def _exit(self):
        return True
