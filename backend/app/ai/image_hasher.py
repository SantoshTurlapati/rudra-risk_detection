import io
from typing import Dict, Any, Union
from PIL import Image

def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Computes difference hash (dHash) of an image:
    1. Resize to (hash_size + 1, hash_size)
    2. Convert to grayscale
    3. Compare adjacent pixels
    """
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.get_flattened_data())

    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)

    # Convert bool array to hex string
    decimal_val = 0
    hex_str = []
    for index, val in enumerate(difference):
        if val:
            decimal_val += 2 ** (index % 4)
        if (index % 4) == 3:
            hex_str.append(hex(decimal_val)[2:])
            decimal_val = 0

    return "".join(hex_str)

def compute_ahash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Computes Average Hash (aHash) of an image.
    """
    resized = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.get_flattened_data())
    avg = sum(pixels) / len(pixels)

    bits = "".join(['1' if p > avg else '0' for p in pixels])
    # Convert bits to hex
    return f"{int(bits, 2):0{hash_size*hash_size//4}x}"

def hamming_distance(hex1: str, hex2: str) -> int:
    """Calculates Hamming distance between two hex hashes."""
    if len(hex1) != len(hex2):
        # normalize length
        max_len = max(len(hex1), len(hex2))
        hex1 = hex1.zfill(max_len)
        hex2 = hex2.zfill(max_len)

    int1 = int(hex1, 16)
    int2 = int(hex2, 16)
    xor_val = int1 ^ int2
    return bin(xor_val).count('1')

def compare_images(
    candidate_img_data: Union[bytes, io.BytesIO],
    reference_img_data: Union[bytes, io.BytesIO]
) -> Dict[str, Any]:
    """
    Compares two images using perceptual difference hashing and returns similarity metrics.
    """
    try:
        if isinstance(candidate_img_data, bytes):
            cand_img = Image.open(io.BytesIO(candidate_img_data))
        else:
            cand_img = Image.open(candidate_img_data)

        if isinstance(reference_img_data, bytes):
            ref_img = Image.open(io.BytesIO(reference_img_data))
        else:
            ref_img = Image.open(reference_img_data)

        cand_dhash = compute_dhash(cand_img)
        ref_dhash = compute_dhash(ref_img)

        cand_ahash = compute_ahash(cand_img)
        ref_ahash = compute_ahash(ref_img)

        dist_dhash = hamming_distance(cand_dhash, ref_dhash)
        dist_ahash = hamming_distance(cand_ahash, ref_ahash)

        # 64 bits total
        # distance <= 10 is considered highly similar
        max_bits = 64
        similarity_dhash = max(0.0, (1.0 - (dist_dhash / max_bits)) * 100.0)
        similarity_ahash = max(0.0, (1.0 - (dist_ahash / max_bits)) * 100.0)

        avg_similarity = round((similarity_dhash * 0.7 + similarity_ahash * 0.3), 1)

        is_suspicious = avg_similarity >= 75.0
        reasons = []
        if avg_similarity >= 95.0:
            reasons.append("Near-identical visual appearance (potential direct logo theft or watermark reuse).")
        elif avg_similarity >= 80.0:
            reasons.append("Very high visual perceptual similarity to official brand logo/icon.")
        elif avg_similarity >= 65.0:
            reasons.append("Moderate visual resemblance detected. May use altered color scheme or framing.")
        else:
            reasons.append("Low visual similarity to official assets.")

        return {
            "similarity_score": avg_similarity,
            "dhash_distance": dist_dhash,
            "ahash_distance": dist_ahash,
            "is_suspicious": is_suspicious,
            "reasons": reasons,
            "candidate_dhash": cand_dhash,
            "reference_dhash": ref_dhash
        }
    except Exception as e:
        return {
            "similarity_score": 0.0,
            "is_suspicious": False,
            "reasons": [f"Visual comparison failed: {str(e)}"],
            "error": str(e)
        }
