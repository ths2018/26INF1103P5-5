class OutputManager:

    HELP_TEXT = (
        "\n===== HEALTHCARE ASSESSMENT CHATBOT =====\n"
        "1. Start a conversation\n"
        "2. View all saved cases\n"
        "3. Browse conversation history\n"
        "4. Export all records to CSV\n"
        "5. Export all records to Excel\n"
        "6. View urgency statistics\n"
        "7. Quit\n"
    )

    def __init__(
        self,
        case_loader=None,
        output_func=None
    ):
        self.case_loader = case_loader

        self._print = (
            output_func
            if output_func is not None
            else print
        )

    def welcome_message(self):
        self._print(self.HELP_TEXT)

    def print_output(self, output):
        self._print(output)

    def print_cases(self):
        if self.case_loader is None:
            raise RuntimeError(
                "A user-scoped case loader must "
                "be provided by the data layer."
            )

        cases = self.case_loader()

        if not cases:
            self._print("No saved cases found.")
            return

        for i, case in enumerate(cases, start=1):
            self._print(f"\nCase {i}: {case}")