from Logic.keywords import EMERGENCY_KEYWORDS
from Logic.text_detector import TextDetector


class EmergencyDetector(TextDetector):
    @property
    def phrases(self):
        return EMERGENCY_KEYWORDS
