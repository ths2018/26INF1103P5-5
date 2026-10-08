from unittest import result
from ai_manager import create_chat
from data_manager import (
    add_log,
    close_case,
    convert_json_to_csv,
    convert_json_to_xlsx,
    create_new_case,
    filter_records_by_keyword,
    get_active_case,
    list_case_files,
    load_case,
    open_file,
    show_history,
)
from logic_manager import is_case_related, process_interaction, menu_selection
from input_output_manager import get_menu_input, get_additional_input, input_manager, create_prompt, ask_yes_no, print_cases, welcome_message
 
def start_new_case(active_case):
    """Closes the current case (if any), creates a new one and a fresh chat."""
    if active_case:
        close_case(active_case)
        print(f"[System] Closed {active_case['case_id']}.json.")
 
    new_case = create_new_case()
    print(f"[System] Created new active case: {new_case['case_id']}.json\n")
    return new_case, create_chat(new_case)

def main():
    welcome_message()

    # Resume the newest case if it is still open, otherwise start a fresh one
    active_case = get_active_case() or create_new_case()
    chat = create_chat(active_case)
    print(f"[System] Active case: {active_case['case_id']}.json "
          f"({len(active_case['logs'])} earlier entries)\n")
 
    while True:
        try:
            user_choice = get_menu_input()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting application. Stay healthy!")
            break

        menu_selection(user_choice)
 
 
if __name__ == "__main__":
    main()