from pathlib import Path
import tarfile, zipfile

def extract_archive(src, out_dir):
    src = Path(src)
    out = Path(out_dir) / src.stem
    out.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            z.extractall(out)
    elif src.suffix.lower() in (".tar", ".gz", ".bz2", ".xz") or src.name.lower().endswith(".tar.gz"):
        with tarfile.open(src, "r:*") as t:
            t.extractall(out)
    else:
        raise ValueError("Built-in archive support currently covers ZIP/TAR/GZ/BZ2/XZ.")
    return out
