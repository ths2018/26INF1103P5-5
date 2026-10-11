import traceback
from ai_manager import create_chat
from input_output_manager import print_output
from data_manager import (
    close_case,
    create_new_case,
    get_active_case,
)
from input_output_manager import (
    get_menu_input,
    welcome_message,
)
from logic_manager import menu_selection
 
def start_new_case(active_case):
    """Closes the current case (if any), creates a new one and a fresh chat."""
    if active_case:
        close_case(active_case)
        print_output(f"[System] Closed {active_case['case_id']}.json.")
 
    new_case = create_new_case()
    print_output(f"[System] Created new active case: {new_case['case_id']}.json\n")
    return new_case, create_chat(new_case)

def main():
    welcome_message()

    try:
        active_case = get_active_case()

        if active_case is None:
            active_case = create_new_case()
            print_output(
                f"[System] Created active case: "
                f"{active_case['case_id']}.json"
            )

        chat = create_chat(active_case)

        print_output(
            f"[System] Active case: "
            f"{active_case['case_id']}.json "
            f"({len(active_case.get('logs', []))} "
            f"saved entries)\n"
        )

    except Exception as exc:
        print_output(
            "[Fatal Error] Could not initialise "
            f"the application: {exc}"
        )
        return

    while True:
        try:
            choice = get_menu_input()

            active_case, chat, should_quit = menu_selection(
                choice,
                active_case,
                chat,
            )

            if should_quit:
                close_case(active_case)

                print_output(
                    f"\n[System] Closed "
                    f"{active_case['case_id']}.json."
                )

                print_output(
                    "Exiting application. Stay healthy!"
                )

                break

        except KeyboardInterrupt:
            print_output(
                "\n\nExiting application. "
                "Stay healthy!"
            )

            if active_case:
                close_case(active_case)

            break

        except EOFError:
            print_output(
                "\n\nInput stream closed. "
                "Exiting application."
            )

            if active_case:
                close_case(active_case)
            break

        except Exception as exc:
            traceback.print_exc()
            print(f"\n[Error] An unexpected error occurred: {type(exc).__name__}: {exc}")
            print("The application will return to the main menu.")


if __name__ == "__main__":
    main()