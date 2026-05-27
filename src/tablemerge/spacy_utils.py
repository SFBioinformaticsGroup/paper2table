import spacy

SPACY_MODELS = {
    "en": "en_core_web_md",
    "es": "es_core_news_md",
}


def load_spacy_model(language: str) -> spacy.language.Language:
    model = SPACY_MODELS.get(language, f"{language}_core_web_md")
    return spacy.load(model)
