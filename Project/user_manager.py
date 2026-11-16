"""
user_manager.py - entry point for user accounts (same style as data_manager.py).

    import user_manager
    user = user_manager.signup_flow()        # prompts, creates folder + db, syncs to Mongo
    user = user_manager.login_flow()
    repo = user_manager.get_service().case_repository(user)   # this user's own cases db
"""

import input_output_manager as io
from userdata import InvalidUserDataError, UserExistsError, UserService

_service = None


def get_service():
    global _service
    if _service is None:
        _service = UserService()
    return _service


def signup_flow():
    """Interactive signup using the existing AuthInputManager prompts."""
    service = get_service()
    email = io.get_email()
    if service.email_exists(email):
        io.display_auth_message("That email is already registered. Please log in instead.")
        return None

    details = io.get_signup_details(email)
    try:
        user = service.create_user(details)
    except (UserExistsError, InvalidUserDataError) as exc:
        io.display_auth_message(f"Could not create account: {exc}")
        return None

    io.display_signup_success()
    io.display_auth_message(f"[System] User folder: users/{user.directory}/")
    if user.sync_status == "synced":
        io.display_auth_message("[System] Synced with MongoDB.")
    else:
        io.display_auth_message(
            "[System] MongoDB unreachable - saved locally, will sync later "
            "(python create_user.py --sync).")
    return user


def login_flow():
    email = io.get_email()
    password = io.get_login_password()
    user = get_service().authenticate(email, password)
    if user is None:
        io.display_login_error()
        return None
    io.display_login_success()
    return user


def sync_pending():
    return get_service().sync_pending()


def to_profile(user):
    """The dict InputManager.input_manager() expects (name, dob, gender...)."""
    return user.public_dict()


def authenticate_flow():
    """Startup gate: log in or sign up. Returns a profile dict, or None to quit."""
    while True:
        io.display_auth_message("\n===== WELCOME =====\n1. Log in\n2. Sign up\n3. Quit")
        choice = input("Choose an option (1-3): ").strip()
        if choice == "1":
            user = login_flow()
        elif choice == "2":
            user = signup_flow()
            if user is not None:       # signup message says "log in", but log them in directly
                io.display_login_success()
        elif choice == "3":
            return None
        else:
            io.display_auth_message("Invalid option. Enter 1, 2 or 3.")
            continue
        if user is not None:
            return to_profile(user)
