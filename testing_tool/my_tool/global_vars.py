#====================================
#========= Configurable Vars ========
#====================================
# The threshold for judging accuracy failures. Between 0-1. Larger the stricter
ACCURACY_THRESHOLD = 0.75

# The maximum number of suggested extra labels.
MAX_CANDIDATE = 3

# The maximum number of shown failed test cases
MAX_INPUT_EXAMPLE = 3


#====================================
#= DO NOT change the following Vars =
#====================================
Client = ["ImageAnnotatorClient", "SpeechClient", "LanguageServiceClient"]
Vision_API = ["face_detection", "text_detection", "document_text_detection", "label_detection", 
"landmark_detection", "logo_detection", "safe_search_detection", "image_properties", "crop_hints", "web_detection", "object_localization", "product_search"]
Speech_API = ["recognize"]
Language_API = ["analyze_sentiment", "classify_text", "analyze_entities", "analyze_entity_sentiment", "analyze_syntax"]

API_Fields = {}
API_Fields["label_detection"] = [("description", "\"\""), ("score", -0.1), ("label_annotations", "\"\""), ("mid", "\"\"")] # label_annotations actually is a complex structure, here is just arbitary value, similar as others
API_Fields["face_detection"] = [("anger_likelihood",1), ("joy_likelihood",1), ("surprise_likelihood",1), ("sorrow_likelihood",1), ("face_bound",0), ("face_annotations", "\"\"")]
API_Fields["text_detection"] = [("description","\"\""), ("text","\"\""), ("type","True"), ("SPACE","True"), ("SURE_SPACE","True"), ("EOL_SURE_SPACE","True"), ("HYPHEN","True"), ("UNKNOWN","True"), ("pages","True"), ("blocks","True"), ("paragraphs","True"), ("words","True"), ("symbols","True"), ("text_annotations", "\"\"")] # type and later fields actually are not boolean. This setting is for efficiency
API_Fields["web_detection"] = [("description", "\"\""), ("score", -0.1), ("web_detection", "\"\"")]
API_Fields["object_localization"] = [("name", "\"\""), ("score", -0.1), ("x", -0.1), ("y", -0.1), ("localized_object_annotations", "\"\""), ("mid", "\"\"")]
API_Fields["landmark_detection"] = [("description", "\"\""), ("score", -0.1), ("landmark_annotations", "\"\"")]

API_Fields["recognize"] = [("transcript", "\"\""), ("confidence", -0.1), ("alternatives", True), ("results", "\"\"")] # alternativesfield actually are not boolean. This setting is for efficiency

API_Fields["analyze_sentiment"] = [("score", -0.1), ("magnitude", -0.1), ("content", "\"\""), ("sentences", "\"\""), ("document_sentiment", "\"\"")]
API_Fields["classify_text"] = [("name", "\"\""), ("confidence", -0.1), ("categories", "\"\"")]
API_Fields["analyze_entities"] = [("name", "\"\""), ("type", 0), ("salience", -0.1), ("metadata", "True"), ("wikipedia_url", ""), ("entities", "\"\"")] # metadata field actually are not boolean. This setting is for efficiency
API_Fields["analyze_entity_sentiment"] = [("name", "\"\""), ("type", 0), ("salience", -0.1), ("metadata", "True"), ("score", -0.1), ("magnitude", -0.1), ("entities", "\"\"")]
API_Fields["analyze_syntax"] = [("tag", -1), ("tokens", "\"\"")] #



Likelihoods = ['UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY']
Entity_Types = ['UNKNOWN', 'PERSON', 'LOCATION', 'ORGANIZATION', 'EVENT', 'WORK_OF_ART', 'CONSUMER_GOOD', 'OTHER', 'PHONE_NUMBER', 'ADDRESS', 'DATE', 'NUMBER', 'PRICE']
Syntax_Types = ['UNKNOWN', 'ADJ', 'ADP', 'ADV', 'CONJ', 'DET', 'NOUN', 'NUM',
               'PRON', 'PRT', 'PUNCT', 'VERB', 'X', 'AFFIX']

# to get an image that must return something
# label detection and web_detection has result even with a white image.
Vision_keyword = {"face_detection": "human face", "landmark_detection": "leaning tower of pisa", "logo_detection": "google logo", "object_localization": "cat", "label_detection": "cat", "web_detection": "cat"}
String_fields = ["description", "text", "name", "transcript", "content"]

# API pairs that are easily misuses
Similar_API_pairs = [
["text_detection", "document_text_detection"],
["label_detection", "object_localization"]
]
Similar_API_mapping = {
    "document_text_detection": {
        "full_text_annotation": "text_annotations[0]",
        "text": "description"
    }, # very limited support on text
    "label_detection": {
        "label_detection": "object_localization",
        "label_annotations":"localized_object_annotations",
        "description":"name",
        "score":"score",
        "mid":"mid",
    },
    "object_localization": {
        "object_localization": "label_detection",
        "localized_object_annotations":"label_annotations",
        "name":"description",
        "score":"score",
        "mid":"mid",
    }
}


# for change_code*.py
LIST_LEN = 3
INLINE_FILE_LINE = 10
# for solve*.py
OUTPUT_PRE_SOLUTION = 20
OUTPUT_PRE_SOLUTION_TEXT = 20
TOTAL_LIMIT = 100
LOCAL_TEST = False # true then only does constaint solving
# LOCAL_TEST = True # test only

GENERATE_AUDIO = True # false then only does constaint solving for audio

# versioning stuff
PYTHON_OHTER = False # true when it is running on python3.6
# PYTHON_OHTER = True # test only
VISION_V1 = False # true if we are using v1, false if v2

# for precondition
MATCH_VALUE = "match our desired output"
SOLVE_PRECONDITION = True

# file path related
INFO_FILE = "extra_info.txt"




