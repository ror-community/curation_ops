import csv
import argparse
from lingua import LanguageDetectorBuilder, Language
import fasttext

#Download from https://fasttext.cc/docs/en/language-identification.html
MODEL_PATH = "model/lid.176.bin"
fasttext_detector = fasttext.load_model(MODEL_PATH)
#Suppress errant warning message
fasttext.FastText.eprint = lambda x: None
lingua_detector = LanguageDetectorBuilder.from_all_languages(
).with_preloaded_language_models().build()


def detect_language_lingua(name):
    try:
        detected_language = lingua_detector.detect_language_of(name)
        return str(detected_language.iso_code_639_1.name).lower()
    except Exception:
        return None


def detect_language_fasttext(name):
    try:
        predictions = fasttext_detector.predict(name, k=1)
        detected_language =  predictions[0][0].split("__label__")[1]
        return detected_language
    except Exception:
        return None


def detect_language_consensus(name):
    lang_lingua = detect_language_lingua(name)
    lang_fasttext = detect_language_fasttext(name)
    if lang_lingua == lang_fasttext:
        return lang_lingua
    return None


def detect_language(name, high_precision):
    if high_precision:
        return detect_language_consensus(name)
    else:
        return detect_language_fasttext(name)



