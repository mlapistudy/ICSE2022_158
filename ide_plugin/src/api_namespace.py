# This file stores the relevant ML API namespace information
# for tracing which functions can be tested

Client = ["ImageAnnotatorClient", "SpeechClient", "LanguageServiceClient"]
Vision_API = ["face_detection", "text_detection", "document_text_detection", "label_detection", 
"landmark_detection", "logo_detection", "safe_search_detection", "image_properties", "crop_hintsn", "web_detection", "object_localization", "product_search"]
Speech_API = ["recognize"]
Language_API = ["analyze_sentiment", "classify_text", "analyze_entities", "analyze_entity_sentiment", "analyze_syntax"]

All_API_Names = []
for vision in Vision_API:
    All_API_Names.append("google.cloud.vision.ImageAnnotatorClient." + vision)
    All_API_Names.append("google.cloud.vision_v1p3beta1.ImageAnnotatorClient." + vision)
    # All_API_Names.append("google.cloud.vision.Client." + vision)
for speech in Speech_API:
    All_API_Names.append("google.cloud.speech.SpeechClient." + speech)
for language in Language_API:
    All_API_Names.append("google.cloud.language.LanguageServiceClient." + language)
    All_API_Names.append("google.cloud.language_v1.LanguageServiceClient." + language)