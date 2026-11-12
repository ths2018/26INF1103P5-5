"""
logic package - one class per file.

Abstract classes ... text_detector.py, ai_service.py
Inheritance ........ health_detector / emergency_detector / memory_question_detector
                     -> text_detector
Interface (ABC) .... ai_service.py  (gemini_ai_service, scripted_ai_service)
Polymorphism ....... AssessmentEngine calls AIService.ask() and TextDetector.detect()
                     without knowing which concrete subclass it holds
Association ........ menu_controller -> assessment_engine, case_repository (uses them)
Aggregation ........ assessment_engine holds an AIService and CaseRepository that are
                     created outside and exist independently
Composition ........ assessment_engine creates and owns its three detectors
Encapsulation ...... _protected, __private, public (see each class)
"""
