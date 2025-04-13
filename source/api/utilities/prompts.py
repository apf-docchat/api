from dataclasses import dataclass


@dataclass(frozen=True)
class StaticPrompts:
    NOUN_CHECK_RETURN_FORMAT = 'Return a JSON object with a single key "nouns". The value should be a comma-separated string of all proper nouns found in the query, without spaces after the commas. If no proper nouns are found, the value should be an empty string. For example:\n{"nouns": "John,New York,Microsoft"}\nor if no proper nouns are found:\n{"nouns": ""}'