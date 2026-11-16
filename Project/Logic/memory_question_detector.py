from Logic.keywords import MEMORY_PHRASES
from Logic.text_detector import TextDetector


class MemoryQuestionDetector(TextDetector):
    @property
    def phrases(self):
        return MEMORY_PHRASES

    def _matches(self, text, phrase):
        # overrides the default: a plain substring match is enough here
        return phrase in text
