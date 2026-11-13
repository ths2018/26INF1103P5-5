
class OutputManager:

    def __init__(self, case_loader=None, output_func=print):
        self.case_loader = case_loader
        self.output_func = output_func

    def welcome_message(self):
        self.output_func("=" * 30)
        self.output_func("HEALTHCARE ASSESSMENT CHATBOT")
        self.output_func("=" * 30)
        self.output_func()

    def print_output(self, output):
        self.output_func(output)

    def print_cases(self):
        if self.case_loader is None:
            raise RuntimeError(
                "Case loader has not been configured."
            )

        cases = self.case_loader()

        self.output_func(
            f"\n{'=' * 20} Saved Cases ({len(cases)}) "
            f"{'=' * 20}"
        )

        if not cases:
            self.output_func("No cases saved yet.")
            return

        for case in cases:
            status = (
                "ACTIVE" if case.is_open() else "CLOSED"
            )

            logs = case.logs

            if logs:
                initial = str(
                    logs[0].user_input
                ).replace("\n", " ")[:50]
            else:
                initial = "Empty"

            self.output_func(
                f"- [{case.case_id}] {status:<6} | "
                f"Logs: {len(logs)} | Initial: {initial}..."
            )

        self.output_func("=" * 70)
