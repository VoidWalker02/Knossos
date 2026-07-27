# knossos/dictionary.py

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree
import re


import httpx

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
DICIONARIO_ABERTO_URL = "https://api.dicionario-aberto.net/word/{word}"


# Raw dc:language values found in real EPUBs are inconsistent, sometimes a
# proper code, sometimes a spelled-out name in the book's own language.
# Maps common variants to codes the API actually accepts.
LANGUAGE_CODE_MAP = {
    "en": "en", "eng": "en", "english": "en", "en-us": "en", "en-gb": "en",
    "pt": "pt-BR", "pt-br": "pt-BR", "por": "pt-BR", "português": "pt-BR", "portuguese": "pt-BR",
}

DEFAULT_DICTIONARY_LANGUAGE = "en"

# The full set the API actually supports, with friendly display names for
# the picker. Order here is the order shown in the picker.
SUPPORTED_LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("pt-BR", "Portuguese (Brazil)"),
]

LANGUAGE_DISPLAY_NAMES = dict(SUPPORTED_LANGUAGES)

def resolve_language_code(raw_language: str | None, fallback: str = DEFAULT_DICTIONARY_LANGUAGE) -> str:
    """Map a raw dc:language value (from EPUB metadata) to a code we
    actually have a dictionary source for. Anything unrecognized or
    unsupported falls back to English."""
    if not raw_language:
        return fallback
    return LANGUAGE_CODE_MAP.get(raw_language.strip().lower(), fallback)


def language_display_name(code: str) -> str:
    return LANGUAGE_DISPLAY_NAMES.get(code, code)    


@dataclass
class WordDefinition:
    part_of_speech: str
    definition: str
    example: str | None = None


@dataclass
class DictionaryResult:
    word: str
    phonetic: str | None
    definitions: list[WordDefinition] = field(default_factory=list)
    source: str = "dictionaryapi.dev"


async def lookup_word(
    word: str, language: str = DEFAULT_DICTIONARY_LANGUAGE, timeout: float = 8.0
) -> DictionaryResult | None:
    """
    Look up a word. English goes through dictionaryapi.dev. Portuguese goes
    straight to Dicionário Aberto, since dictionaryapi.dev's pt-BR coverage
    was confirmed empty during testing. Any other language code falls back
    to English behavior (should not normally happen, since the picker only
    offers en/pt-BR — see resolve_language_code).
    """
    if language == "pt-BR":
        return await _lookup_word_dicionario_aberto(word, timeout)

    return await _lookup_word_primary(word, language, timeout)


async def _lookup_word_primary(word: str, language: str, timeout: float) -> DictionaryResult | None:
    url = DICTIONARY_API_URL.format(language=language, word=word.strip().lower())

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if not isinstance(data, list) or not data:
        return None

    entry = data[0]
    phonetic = entry.get("phonetic")

    definitions: list[WordDefinition] = []
    for meaning in entry.get("meanings", []):
        part_of_speech = meaning.get("partOfSpeech", "")
        for d in meaning.get("definitions", []):
            definition_text = d.get("definition")
            if not definition_text:
                continue
            definitions.append(
                WordDefinition(part_of_speech=part_of_speech, definition=definition_text, example=d.get("example"))
            )

    if not definitions:
        return None

    return DictionaryResult(word=entry.get("word", word), phonetic=phonetic, definitions=definitions)


    

def _parse_dicionario_aberto_entry(xml_text: str) -> WordDefinition | None:
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
    except (etree.XMLSyntaxError, ValueError):
        return None

    gram_el = root.find(".//gramGrp")
    part_of_speech = (gram_el.text or "").strip() if gram_el is not None else ""

    def_el = root.find(".//def")
    if def_el is None:
        return None

    definition_text = " ".join(def_el.itertext()).strip()
    if not definition_text:
        return None

    definition_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", definition_text)
    definition_text = definition_text.replace("_", "")
    definition_text = re.sub(r"\s+", " ", definition_text).strip()

    return WordDefinition(part_of_speech=part_of_speech, definition=definition_text)


async def _lookup_word_dicionario_aberto(word: str, timeout: float) -> DictionaryResult | None:
    url = DICIONARIO_ABERTO_URL.format(word=word.strip().lower())

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=timeout)
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if not isinstance(data, list) or not data:
        return None

    definitions: list[WordDefinition] = []
    for item in data:
        xml_text = item.get("xml")
        if not xml_text:
            continue
        parsed = _parse_dicionario_aberto_entry(xml_text)
        if parsed is not None:
            definitions.append(parsed)

    if not definitions:
        return None

    return DictionaryResult(word=word, phonetic=None, definitions=definitions, source="Dicionário Aberto")




