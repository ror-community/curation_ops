import csv
import argparse
import fasttext
from lingua import LanguageDetectorBuilder, Language

MODEL_PATH = "lid.176.bin"
fasttext_detector = fasttext.load_model(MODEL_PATH)
lingua_detector = LanguageDetectorBuilder.from_all_languages(
).with_preloaded_language_models().build()


def load_common_languages(file_path):
    common_languages = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            country, languages = row['Country'], row['Most Common Languages']
            common_languages[country] = [lang.strip()
                                         for lang in languages.split(';')]
    return common_languages


def detect_language_lingua(label):
    try:
        detected_language = lingua_detector.detect_language_of(label)
        return str(detected_language.iso_code_639_1.name).lower()
    except Exception:
        return None


def detect_language_fasttext(label):
    try:
        predictions = fasttext_detector.predict(label, k=1)
        detected_language = predictions[0][0].split("__label__")[1]
        return detected_language
    except Exception:
        return None


def detect_language(label, country, common_languages):
    lang_fasttext = detect_language_fasttext(label)
    lang_lingua = detect_language_lingua(label)
    if lang_fasttext == lang_lingua:
        return lang_fasttext
    if country in common_languages:
        if lang_fasttext in common_languages[country] or lang_lingua in common_languages[country]:
            return lang_fasttext if lang_fasttext in common_languages[country] else lang_lingua
    return None

