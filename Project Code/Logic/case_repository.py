from data_manager import (
    add_log,
    close_case,
    convert_json_to_csv,
    convert_json_to_xlsx,
    create_new_case,
    filter_records_by_keyword,
    get_active_case,
    open_file,
    show_history,
)


class CaseRepository:
    """Everything that reads/writes patient cases and records (wraps data_manager)."""

    def get_active_case(self):
        return get_active_case()

    def create_case(self):
        return create_new_case()

    def close_case(self, case):
        close_case(case)

    def add_log(self, case, user_input, ai_response):
        add_log(case, user_input, ai_response)

    def search(self, keyword):
        return filter_records_by_keyword(keyword)

    def show_history(self, records):
        show_history(records)

    def export_csv(self):
        convert_json_to_csv()

    def export_xlsx_and_open(self):
        if convert_json_to_xlsx():
            open_file()
