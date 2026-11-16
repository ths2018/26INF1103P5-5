"""HistoryViewer: paginated viewer for a list of records."""


import input_output_manager


class HistoryViewer:
    """Paginated viewer. ASSOCIATION: works on a list of records it does not own."""

    def __init__(self, records, page_size=2):
        self._records = records
        self._page_size = page_size

    def show(self):
        results = self._records
        page_size = self._page_size
        total_records = len(results)
        total_pages = (total_records + page_size - 1) // page_size
        current_page = 0

        while True:
            start_idx = current_page * page_size
            page_items = results[start_idx:start_idx + page_size]

            input_output_manager.print_output(
                f"\n{'=' * 20} History (Page {current_page + 1} of {total_pages}) {'=' * 20}")

            for idx, record in enumerate(page_items, start=start_idx + 1):
                input_output_manager.print_output(
                    f"\n[Record #{idx}/{total_records}] {record.get('case_id', '')} - {record['timestamp']}")
                input_output_manager.print_output(f"User Question:\n{record['user_input']}")
                input_output_manager.print_output(f"\nFull AI Response:\n{record['ai_response']}")
                input_output_manager.print_output("-" * 60)

            nav_options = []
            if current_page < total_pages - 1:
                nav_options.append("'n' for next page")
            if current_page > 0:
                nav_options.append("'p' for previous page")
            nav_options.append("'q' to exit search")

            action = input(f"\nNavigation [{', '.join(nav_options)}]: ").strip().lower()

            if action == "n" and current_page < total_pages - 1:
                current_page += 1
            elif action == "p" and current_page > 0:
                current_page -= 1
            elif action in ("q", "exit", "quit"):
                input_output_manager.print_output("Exited history view.")
                break
            else:
                input_output_manager.print_output("Invalid option or end of pages reached.")
