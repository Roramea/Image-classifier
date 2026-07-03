import os
import hashlib
from PIL import Image
import math


def compute_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def dhash(image: Image.Image, hash_size: int = 8) -> str:
    try:
        resample_method = Image.Resampling.LANCZOS
    except AttributeError:
        resample_method = Image.LANCZOS
    image = image.convert('L').resize((hash_size + 1, hash_size), resample_method)
    pixels = list(image.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** (index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
    return ''.join(hex_string)


def hamming_distance(s1: str, s2: str) -> int:
    if not s1 or not s2 or len(s1) != len(s2):
        return float('inf')
    
    distance = 0
    for c1, c2 in zip(s1, s2):
        if c1 != c2:
            nibble1 = int(c1, 16)
            nibble2 = int(c2, 16)
            xor = nibble1 ^ nibble2
            distance += bin(xor).count('1')
    return distance


def compute_image_hash(file_path: str) -> str:
    try:
        with Image.open(file_path) as img:
            img = img.convert('RGB')
            return dhash(img)
    except Exception:
        return ""