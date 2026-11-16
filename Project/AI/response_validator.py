
import json
import re


class ResponseValidator:
    REQUIRED_FIELDS = {
        "urgency_classification",
        "certainty",
        "follow_up_question",
        "next_step_guidance"
    }

    ALLOWED_URGENCY = {
        "emergency",
        "urgent",
        "non-urgent",
        "insufficient_information"
    }

    def validate(self, response):
        """Parses and validates the AI JSON response."""
        if not isinstance(response, str) or not response.strip():
            raise ValueError("AI returned an empty response.")

        # Remove Markdown code fences if present.
        response = response.strip()
        response = re.sub(r"^```(?:json)?\s*","",response,flags=re.IGNORECASE)
        response = re.sub(r"\s*```$", "", response)

        # Parse JSON.
        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON response.") from exc

        if not isinstance(data, dict):
            raise ValueError("Response must be a JSON object.")

        # Check required fields.
        missing = self.REQUIRED_FIELDS - data.keys()

        if missing:
            raise ValueError(f"Missing fields: {missing}")

        # Check urgency classification.
        if data["urgency_classification"] not in self.ALLOWED_URGENCY:
            raise ValueError("Invalid urgency classification.")

        # Check certainty.
        certainty = data["certainty"]

        if (
            isinstance(certainty, bool)
            or not isinstance(certainty, (int, float))
            or not 0 <= certainty <= 100
        ):
            raise ValueError("Certainty must be between 0 and 100.")

        # Check text fields.
        if not isinstance(data["follow_up_question"], str):
            raise ValueError("Follow-up question must be a string.")

        if not isinstance(data["next_step_guidance"], str):
            raise ValueError("Next-step guidance must be a string.")

        # Check consistency between certainty and urgency.
        if certainty < 95:

            if data["urgency_classification"] != "insufficient_information":
                raise ValueError("Certainty below 95 requires insufficient_information.")

            if not data["follow_up_question"].strip():
                raise ValueError("A follow-up question is required.")

            if data["next_step_guidance"] != "Not yet - more information needed":
                raise ValueError("Guidance must not be provided below 80% certainty.")

        else:

            if data["urgency_classification"] == "insufficient_information":
                raise ValueError("A final urgency classification is required.")

            if data["follow_up_question"].strip():
                raise ValueError("Follow-up question must be empty at 80% or higher.")

            if not data["next_step_guidance"].strip():
                raise ValueError("Next-step guidance is required.")

        return data
