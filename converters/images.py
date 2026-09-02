from pathlib import Path
from PIL import Image
from core.engine import unique_path

IMAGE_FORMATS = {
    "PNG": ".png", "JPEG": ".jpg", "WebP": ".webp",
    "AVIF": ".avif", "BMP": ".bmp", "TIFF": ".tiff",
    "GIF": ".gif", "ICO": ".ico",
}

def convert_image(src, out_dir, fmt, quality=90, size=None):
    src = Path(src)
    dst = unique_path(Path(out_dir) / (src.stem + IMAGE_FORMATS[fmt]))
    img = Image.open(src)
    if size:
        img.thumbnail(size, Image.Resampling.LANCZOS)
    if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.getchannel("A"))
        img = bg
    elif fmt in ("PNG", "WebP", "ICO") and img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    kwargs = {"quality": quality} if fmt in ("JPEG", "WebP") else {}
    if fmt == "ICO":
        img.save(dst, format="ICO",
                 sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    else:
        img.save(dst, format=fmt, **kwargs)
    return dst

def images_to_gif(paths, out_dir, duration=120):
    frames = [Image.open(p).convert("RGBA") for p in paths]
    if not frames:
        raise ValueError("No images selected.")
    dst = unique_path(Path(out_dir) / "animation.gif")
    frames[0].save(dst, format="GIF", save_all=True,
                   append_images=frames[1:], duration=duration,
                   loop=0, disposal=2)
    return dst
