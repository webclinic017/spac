from typing import Dict
import re
import collections


HEADER = (
    'financial accounting standards provided pursuant '
    'to section 13(a) of the exchange act'
)
FOOTER = (
    'signature pursuant to the requirements of '
    'the securities exchange act of 1934'
)


def _search_text(txt: str, prefix: str, suffix: str) -> str:
    """Find text in between prefix and suffix.

    If suffix is "" find all text post prefix.
    Args:
        prefix: String prefix which parameterizes start index.
        suffix: String suffix which parameterizes end index.
    Return:
        String text in between suffix and prefix.
    """
    try:
        start = txt.index(prefix) + len(prefix)
        end = txt.index(suffix) if suffix is not "" else len(txt)
        return txt[start:end]
    except ValueError:
        return ""


def preprocess_document(text: str) -> str:
    """Initial pre-processing for SEC text document.

    Given a string document, remove all new line characters, unicode characters
    and repeated spaces. Then lower case the text. Finally remove the header
    and footer of the doc.
    Args:
        text: String of document text.
    Returns:
        String for processed document text.
    """
    # Replace new line and tabs.
    text = text.replace('\n', ' ').replace('\t', ' ')

    # Replace unicode characters.
    unicode_replacements = {
        '\xa0': ' ', '\x93': '"', '”': '"', '“': '"'
    }
    for unicode, replacement in unicode_replacements.items():
        text = text.replace(unicode, replacement)

    # Remove extra spaces.
    text = re.sub(' +', ' ', text)
    text = text.lower()

    # Remove everything in header and footer.
    text = _search_text(text, HEADER, FOOTER)
    return text


def get_items_mapping(text: str) -> Dict[str, str]:
    """Get subheaders and associated subtext.

    Parse out all subheaders and create a mapping from subheader to its
    corresponding subtext. A subheader is of the form "item 7.01" and the
    associated subtext follows said subheader until the next item.
    Args:
        String SEC filing document.
    Returns:
        Dictionary mapping subheader to subtext.
    """
    # Extract subheaders and get rid of duplicates
    subheaders = re.findall('item [0-9]+\.[0-9]+', text)
    subheaders = list(set(subheaders))
    subheaders.sort()

    # Map subheader to its associated text.
    item_mapping = {}
    for i, subheader in enumerate(subheaders):
        if i >= len(subheaders) - 1:
            subtext = _search_text(text, subheader, "")
        else:
            subtext = _search_text(text, subheader, subheaders[i + 1])
        item_mapping[subheader] = subtext
    return item_mapping

