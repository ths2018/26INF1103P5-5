from Logic.keywords import HEALTH_KEYWORDS
from Logic.text_detector import TextDetector


class HealthDetector(TextDetector):
    @property
    def phrases(self):
        return HEALTH_KEYWORDS
