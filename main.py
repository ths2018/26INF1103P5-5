from ai_manager import ask_ai, create_chat
from data_manager import save_record

def main():
    print("==============================")
    print("    HEALTHCARE ASSESSMENT CHATBOT  ")
    print("==============================")
    print("Type 'quit' to exit.")
    print()

    chat = create_chat()

    while True:

        user_input = input("Enter your symptoms/question: ").strip()

        if user_input.lower() == "quit":
            print("Exiting application.")
            break

        if user_input == "":
            print("Please enter something.")
            continue
        print("\nSending to AI...")

        ai_response = ask_ai(chat,user_input)

        if ai_response is None:
            print("\nAI service is currently unavailable.")
            print("Please try again later.")
            continue

        print("\n==============================")
        print("             AI")
        print("==============================")
        print(ai_response)
        print("==============================")

        save_record(
            user_input,
            ai_response
        )
        print("Assessment saved.\n")

if __name__ == "__main__":
    main()