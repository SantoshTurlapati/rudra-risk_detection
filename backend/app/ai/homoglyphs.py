import unicodedata
from typing import Tuple, List

# Common homoglyph mappings (Cyrillic, Greek, Math variants to Latin ASCII)
HOMOGLYPH_MAP = {
    # Cyrillic
    'а': 'a', 'А': 'A',
    'в': 'b', 'В': 'B',
    'с': 'c', 'С': 'C',
    'е': 'e', 'Е': 'E',
    'і': 'i', 'І': 'I',
    'ј': 'j', 'Ј': 'J',
    'к': 'k', 'К': 'K',
    'м': 'm', 'М': 'M',
    'н': 'h', 'Н': 'H',
    'о': 'o', 'О': 'O',
    'р': 'p', 'Р': 'P',
    'ѕ': 's', 'Ѕ': 'S',
    'т': 't', 'Т': 'T',
    'у': 'y', 'У': 'Y',
    'х': 'x', 'Х': 'X',
    # Greek
    'α': 'a', 'Α': 'A',
    'β': 'b', 'Β': 'B',
    'γ': 'y', 'Γ': 'r',
    'ε': 'e', 'Ε': 'E',
    'η': 'n', 'Η': 'H',
    'ι': 'i', 'Ι': 'I',
    'κ': 'k', 'Κ': 'K',
    'ν': 'v', 'Ν': 'N',
    'ο': 'o', 'Ο': 'O',
    'ρ': 'p', 'Ρ': 'P',
    'τ': 't', 'Τ': 'T',
    'χ': 'x', 'Χ': 'X',
    # Latin lookalikes & zero-widths
    '\u200b': '', # Zero-width space
    '\u200c': '', # Zero-width non-joiner
    '\u200d': '', # Zero-width joiner
    '\ufeff': '', # Zero-width no-break space
    '0': 'o',     # Common digit substitution
    '1': 'l',     # Digit 1 to l
    '3': 'e',     # Leetspeak 3 to e
    '5': 's',     # Leetspeak 5 to s
}

def detect_and_normalize_homoglyphs(text: str) -> Tuple[str, List[str], bool]:
    """
    Normalizes text to ASCII equivalents and detects deceptive homoglyphs or hidden characters.
    Returns: (normalized_text, detected_anomalies, has_deception)
    """
    if not text:
        return "", [], False

    # Normalize Unicode NFKD
    decomposed = unicodedata.normalize('NFKD', text)

    anomalies = []
    normalized_chars = []

    for char in decomposed:
        code_point = ord(char)
        char_name = unicodedata.name(char, 'UNKNOWN')

        # Check if character is non-ASCII
        if char in HOMOGLYPH_MAP:
            mapped = HOMOGLYPH_MAP[char]
            if ord(char) > 127:
                anomalies.append(f"Homoglyph character '{char}' (U+{code_point:04X} {char_name}) mimicking '{mapped}'")
            normalized_chars.append(mapped)
        elif code_point in [0x200B, 0x200C, 0x200D, 0xFEFF]:
            anomalies.append(f"Hidden zero-width character (U+{code_point:04X}) detected")
        else:
            normalized_chars.append(char)

    normalized_text = "".join(normalized_chars).lower()
    has_deception = len(anomalies) > 0
    return normalized_text, anomalies, has_deception
