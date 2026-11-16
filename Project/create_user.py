"""Run:  python create_user.py          -> create a user (folder + db + MongoDB sync)
        python create_user.py --sync   -> push accounts that were saved while Mongo was offline
"""
import sys

import user_manager

if __name__ == "__main__":
    if "--sync" in sys.argv:
        print(f"Synced {user_manager.sync_pending()} account(s) to MongoDB.")
    else:
        user_manager.signup_flow()
