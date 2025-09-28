import string
import unicodedata

def normalize_name(name: str | None):
    if name == None:
        return None

    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    valid = string.ascii_lowercase + string.digits + "_"
    name = name.lower()
    name = "".join(ch if ch in valid else "_" for ch in name)
    while "__" in name:
        name = name.replace("__", "_")
    return name.strip("_")