import hashlib
import io
import warnings
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000


@dataclass(frozen=True)
class ValidatedImage:
    media_type: str
    format: str
    width: int
    height: int
    content_hash: str


def validate_image_bytes(data: bytes) -> ValidatedImage:
    if not data:
        raise ValueError("Image file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image file exceeds 10MB limit.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                width, height = image.size
                if image_format not in ALLOWED_IMAGE_TYPES:
                    raise ValueError(
                        "Unsupported image format. Use PNG, JPEG, or WebP."
                    )
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise ValueError(
                        "Image dimensions exceed the supported pixel limit."
                    )
                image.load()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
    ) as exc:
        raise ValueError("Invalid or corrupt image file.") from exc

    return ValidatedImage(
        media_type=ALLOWED_IMAGE_TYPES[image_format],
        format=image_format,
        width=width,
        height=height,
        content_hash=hashlib.sha256(data).hexdigest(),
    )
