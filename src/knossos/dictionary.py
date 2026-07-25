# knossos/dictionary.py

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


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


async def lookup_word(word: str, timeout: float = 8.0) -> DictionaryResult | None:
    """
    Look up a word via the free dictionaryapi.dev API. Returns None if the
    word isn't found, the request fails, or the response is malformed —
    callers should treat None as "no definition available" and fail
    gracefully rather than crashing the reader over a lookup miss.
    """
    url = DICTIONARY_API_URL.format(word=word.strip().lower())

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        # 404 (word not found) and other non-success codes return a
        # single error object, not the array we expect on success.
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
                WordDefinition(
                    part_of_speech=part_of_speech,
                    definition=definition_text,
                    example=d.get("example"),
                )
            )

    if not definitions:
        return None

    return DictionaryResult(word=entry.get("word", word), phonetic=phonetic, definitions=definitions)
