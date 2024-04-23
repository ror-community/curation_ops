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
        confidence_values = lingua_detector.compute_language_confidence_values(
            label)
        sorted_confidence_values = sorted(
            confidence_values, key=lambda x: x.value, reverse=True)[:5]
        return [(conf.language.iso_code_639_1.name.lower(), conf.value) for conf in sorted_confidence_values]
    except Exception:
        return None


def detect_language_fasttext(label):
    try:
        predictions = fasttext_detector.predict(label, k=5)
        return [(lang.split("__label__")[1], score) for lang, score in zip(*predictions)]
    except Exception:
        return None


def detect_language(label, country, common_languages):
    lang_predictions_fasttext = detect_language_fasttext(label)
    lang_predictions_lingua = detect_language_lingua(label)
    if lang_predictions_fasttext and lang_predictions_lingua:
        if lang_predictions_fasttext[0][0] == lang_predictions_lingua[0][0]:
            return lang_predictions_fasttext[0][0]
        if country in common_languages:
            for lang_fasttext, fcs in lang_predictions_fasttext:
                for lang_lingua, lcs in lang_predictions_lingua:
                    combined_confidence = fcs + lcs
                    if lang_fasttext == lang_lingua and lang_fasttext != 'en' and lang_fasttext in common_languages[country] and combined_confidence >= .5:
                        return lang_fasttext
                    if lang_fasttext == lang_lingua and lang_fasttext == 'en' and lang_fasttext and combined_confidence >= .5:
                        return lang_fasttext
        for lang, _ in lang_predictions_fasttext:
            if country in common_languages and lang in common_languages[country]:
                return lang
        for lang, _ in lang_predictions_lingua:
            if country in common_languages and lang in common_languages[country]:
                return lang
    return None
