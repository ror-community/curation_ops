import fasttext


MODEL_PATH = "lid.176.bin"
# Suppress erroneous error message on loading model that Meta never fixed
# https://github.com/facebookresearch/fastText/issues/1067
fasttext.FastText.eprint = lambda x: None
detector = fasttext.load_model(MODEL_PATH)


def detect_language(label):
    try:
        predictions = detector.predict(label, k=1)
        detected_language = predictions[0][0].split("__label__")[1]
        return detected_language
    except Exception as e:
        return None
