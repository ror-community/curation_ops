import csv
import argparse
from lingua import LanguageDetectorBuilder, Language
import fasttext

MODEL_PATH = "lid.176.bin"
fasttext_detector = fasttext.load_model(MODEL_PATH)
lingua_detector = LanguageDetectorBuilder.from_all_languages(
).with_preloaded_language_models().build()


def detect_language_lingua(label):
    try:
        detected_language = lingua_detector.detect_language_of(label)
        return str(detected_language.iso_code_639_1.name).lower()
    except Exception:
        return None


def detect_language_fasttext(label):
    try:
        predictions = fasttext_detector.predict(label, k=1)
        detected_language =  predictions[0][0].split("__label__")[1]
        return detected_language
    except Exception:
        return None


def detect_language(label):
    lang_fasttext = detect_language_fasttext(label)
    lang_lingua = detect_language_lingua(label)
    if lang_fasttext == lang_lingua:
        return lang_fasttext
    return None
