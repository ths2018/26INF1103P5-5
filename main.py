from ai_manager import ask_ai, check_relevance, create_chat
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
 
HELP_TEXT = """Commands:
  quit                 exit the program
  cases                list all saved cases
  new                  close the current case and start a new one
  history [keyword]    browse past entries (optionally filtered by keyword)
  export               save all records to CSV
  export xlsx          save all records to Excel and open it"""
 
 
def ask_yes_no(prompt):
    """Keeps asking until the user answers y or n."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")
 
 
def start_new_case(active_case):
    """Closes the current case (if any), creates a new one and a fresh chat."""
    if active_case:
        close_case(active_case)
        print(f"[System] Closed {active_case['case_id']}.json.")
 
    new_case = create_new_case()
    print(f"[System] Created new active case: {new_case['case_id']}.json\n")
    return new_case, create_chat(new_case)
 
 
def print_cases():
    files = list_case_files()
    print(f"\n{'=' * 20} Saved Cases ({len(files)}) {'=' * 20}")
    if not files:
        print("No cases saved yet.")
        return
 
    for path in files:
        case = load_case(path)
        if not case:
            continue
        status = "ACTIVE" if case["status"] == "open" else "CLOSED"
        logs = case["logs"]
        initial = logs[0]["user_input"][:30] if logs else "Empty"
        print(f"- [{case['case_id']}.json] {status:<6} | Logs: {len(logs)} | Initial: {initial}...")
    print("=" * 58)
 
 
def main():
    print("==============================")
    print("   HEALTHCARE ASSESSMENT CHATBOT")
    print("==============================")
    print(HELP_TEXT)
    print()
 
    # Resume the newest case if it is still open, otherwise start a fresh one
    active_case = get_active_case() or create_new_case()
    chat = create_chat(active_case)
    print(f"[System] Active case: {active_case['case_id']}.json "
          f"({len(active_case['logs'])} earlier entries)\n")
 
    while True:
        try:
            user_input = input("Enter your symptoms/question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting application. Stay healthy!")
            break
 
        command = user_input.lower()
 
        # --- Commands: handled locally, never sent to the AI ---
        if not user_input:
            print("Please enter something.")
            continue
 
        if command == "quit":
            print("Exiting application. Stay healthy!")
            break
 
        if command == "cases":
            print_cases()
            continue
 
        if command in ("new", "new case"):
            if not active_case["logs"]:
                print("[System] The current case is already empty, so there is nothing to close.\n")
            else:
                active_case, chat = start_new_case(active_case)
            continue
 
        if command == "export":
            convert_json_to_csv()
            continue
 
        if command == "export xlsx":
            if convert_json_to_xlsx():
                open_file()
            continue
 
        if command == "history" or command.startswith("history "):
            keyword = user_input[len("history"):].strip()
            results = filter_records_by_keyword(keyword)
            if not results:
                print(f"\nNo matching records found for '{keyword}'.")
            else:
                show_history(results)
            continue
 
        # --- Case routing: decide which case this message belongs to ---
        if active_case["logs"] and not check_relevance(user_input, active_case):
            first_entry = active_case["logs"][0]["user_input"][:30]
            print(f"\n[System] This looks unrelated to {active_case['case_id']}.json.")
            if not ask_yes_no(f"Is it related to your earlier entry ({first_entry}...)? (y/n): "):
                active_case, chat = start_new_case(active_case)
            else:
                print(f"[System] Continuing with {active_case['case_id']}.json\n")
 
        # --- Ask the AI ---
        print("\nSending to AI...")
        ai_response = ask_ai(chat, user_input)
 
        if ai_response is None:
            print("\nAI service is currently unavailable.")
            print("Please try again later, or seek professional medical help if needed.\n")
            continue
 
        print("\n==============================")
        print("             AI")
        print("==============================")
        print(ai_response)
        print("==============================")
 
        if add_log(active_case, user_input, ai_response):
            print(f"Assessment saved to {active_case['case_id']}.json.\n")
 
 
if __name__ == "__main__":
    main()