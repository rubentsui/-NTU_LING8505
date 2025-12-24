from src.tm import TranslationMemory

# Global TM instance
tm = TranslationMemory()

def search_tm_exact(query: str):
    """
    Searches for an exact match of the query sentence in the translation memory.
    Returns a list of matches with 'source' and 'target'.
    """
    return tm.search_exact(query)

def search_tm_semantic(query: str):
    """
    Searches for semantically similar sentences in the translation memory.
    Returns a list of matches with 'source', 'target', and 'distance'.
    """
    return tm.search_semantic(query)

def write_translation(file_path: str, content: str):
    """
    Writes the translated content to a file.
    This acts as the 'Output editor'.
    """
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content + "\n")
    return f"Appended translation to {file_path}"

