import os
import traceback
from AI.ai_manager import AIManager
ai_manager = AIManager()
from input_output_manager import print_output
from data_manager import (
    close_case,
    create_new_case,
    get_active_case,
    get_backend_name,
    set_current_user,
)
from input_output_manager import (
    get_menu_input,
    welcome_message,
)
from logic_manager_oop import menu_selection
import input_output_manager as io_manager
from Logic.argon2_password_hasher import Argon2PasswordHasher
from Logic.auth_controller import AuthController
from Logic.auth_service import AuthService
from Logic.in_memory_user_repository import InMemoryUserRepository


def build_user_repository():
    """Where user accounts are stored (the ONE place to change when the user
    database is ready).

    Set USER_DB_URI in your .env to use MongoDB (optionally USER_DB_NAME and
    USER_DB_COLLECTION). Until then, accounts are kept in memory only.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    uri = os.getenv("USER_DB_URL")
    if not uri:
        print_output(
            "[Warning] No user database configured (USER_DB_URI is not set). "
            "Accounts are kept in memory only and are lost when the program closes."
        )
        return InMemoryUserRepository()

    from pymongo import MongoClient
    from Logic.mongo_user_repository import MongoUserRepository

    database = MongoClient(uri)[os.getenv("USER_DB_NAME", "case_assessments")]
    return MongoUserRepository(database[os.getenv("USER_DB_COLLECTION", "users")])


def authenticate():
    """Sign-in gate. Returns the signed-in user's profile (a dict with 'email'),
    or None if the user chose to exit."""
    auth_service = AuthService(Argon2PasswordHasher(), build_user_repository())
    return AuthController(auth_service, io_manager).run()
 
def start_new_case(active_case):
    """Closes the current case (if any), creates a new one and a fresh chat."""
    if active_case:
        close_case(active_case)
        print_output(f"[System] Closed {active_case.case_id}.")
 
    new_case = create_new_case()
    print_output(f"[System] Created new active case: {new_case.case_id}\n")
    return new_case, ai_manager.create_chat(new_case)

def main():
    # The user must sign in (or sign up, then sign in) before anything else runs.
    try:
        user = authenticate()
    except (KeyboardInterrupt, EOFError):
        user = None
    if user is None:
        print_output("\nExiting application. Stay healthy!")
        return
    set_current_user(user["user_id"])
    print_output(f"[System] Signed in as {user['email']}\n")

    welcome_message()  # the main menu is only shown after signing in

    try:
        active_case = get_active_case()
        print_output(f"[System] Storage backend: {get_backend_name()}")

        if active_case is None:
            active_case = create_new_case()
            print_output(
                f"[System] Created active case: "
                f"{active_case.case_id}"
            )

        chat = ai_manager.create_chat(active_case)

        print_output(
            f"[System] Active case: "
            f"{active_case.case_id} "
            f"({len(active_case.logs)} "
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
                user,
            )

            if should_quit:
                close_case(active_case)

                print_output(
                    f"\n[System] Closed "
                    f"{active_case.case_id}."
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
            print_output(f"\n[Error] An unexpected error occurred: {type(exc).__name__}: {exc}")
            print_output("The application will return to the main menu.")


if __name__ == "__main__":
    main()