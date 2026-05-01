import cv2
import numpy as np
import random
import os
import tempfile

def _check_image(img, action="encode"):
    if img is None:
        raise ValueError("Could not read image. File may be corrupted.")
    h, w = img.shape[:2]
    total_pixels = h * w
    if w < 10 or h < 10:
        raise ValueError("Image too small. Minimum 10x10 pixels.")
    if total_pixels <= 12:
        raise ValueError("Image too small. Need at least 13 pixels.")
    if total_pixels > 25_000_000:
        raise ValueError("Image too large. Maximum 25 megapixels.")
    
    usable_pixels = total_pixels - 12
    max_chars = usable_pixels // 3
    return h, w, total_pixels, max_chars

def encode_image(input_path, message, output_path):
    if not message or not message.strip():
        raise ValueError("Message cannot be empty.")
        
    for c in message:
        if ord(c) > 127:
            raise ValueError(f"Message contains unsupported characters. Use ASCII only (no emoji or special symbols). Problematic character: {c}")

    img = cv2.imread(input_path, cv2.IMREAD_COLOR)
    h, w, total_pixels, max_chars = _check_image(img, "encode")
    
    length = len(message)
    if length > max_chars:
        raise ValueError(f"Message too long. Max {max_chars} characters for this image.")

    key = random.randint(0, 65535)

    def store_bits(img, start_pixel, value, num_bits):
        bit_index = 0
        for p in range(start_pixel, start_pixel + 6):
            r = p // w
            c = p % w
            pixel = img[r, c].copy()
            for ch in range(3):
                if bit_index < num_bits:
                    bit = (value >> (num_bits - 1 - bit_index)) & 1
                    pixel[ch] = (int(pixel[ch]) & 0xFE) | bit
                    bit_index += 1
            img[r, c] = pixel

    store_bits(img, 0, key, 16)
    store_bits(img, 6, length, 16)

    rng = random.Random(key)
    all_positions = [(r, c) for r in range(h) for c in range(w)
                     if (r * w + c) >= 12]
    
    used = set()
    selected = []
    required_pixels = length * 3
    
    max_attempts = total_pixels * 10
    attempts = 0
    for _ in range(required_pixels):
        while True:
            attempts += 1
            if attempts > max_attempts:
                raise RuntimeError("RNG exhausted — image too small for this message")
            idx = rng.randint(0, len(all_positions) - 1)
            if idx not in used:
                used.add(idx)
                selected.append(all_positions[idx])
                break

    for i, char in enumerate(message):
        data = ord(char)
        p1 = selected[i * 3]
        p2 = selected[i * 3 + 1]
        p3 = selected[i * 3 + 2]

        pixel1 = img[p1[0], p1[1]].copy()
        pixel1[0] = (int(pixel1[0]) & 0xFE) | ((data >> 7) & 1)
        pixel1[1] = (int(pixel1[1]) & 0xFE) | ((data >> 6) & 1)
        pixel1[2] = (int(pixel1[2]) & 0xFE) | ((data >> 5) & 1)
        img[p1[0], p1[1]] = pixel1

        pixel2 = img[p2[0], p2[1]].copy()
        pixel2[0] = (int(pixel2[0]) & 0xFE) | ((data >> 4) & 1)
        pixel2[1] = (int(pixel2[1]) & 0xFE) | ((data >> 3) & 1)
        pixel2[2] = (int(pixel2[2]) & 0xFE) | ((data >> 2) & 1)
        img[p2[0], p2[1]] = pixel2

        pixel3 = img[p3[0], p3[1]].copy()
        pixel3[0] = (int(pixel3[0]) & 0xFE) | ((data >> 1) & 1)
        pixel3[1] = (int(pixel3[1]) & 0xFE) | ((data >> 0) & 1)
        img[p3[0], p3[1]] = pixel3

    success = cv2.imwrite(output_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    if not success:
        raise RuntimeError("Failed to write output PNG")
    return key

def decode_image(input_path):
    with open(input_path, 'rb') as f:
        magic = f.read(8)
        if not magic.startswith(b'\x89PNG'):
            raise ValueError("Decode requires a PNG file. JPG/WEBP will not work as they alter pixel values.")
            
    img = cv2.imread(input_path, cv2.IMREAD_COLOR)
    h, w, total_pixels, max_chars = _check_image(img, "decode")

    def read_bits(img, start_pixel, num_bits):
        val = 0
        bit_index = 0
        for p in range(start_pixel, start_pixel + 6):
            r = p // w
            c = p % w
            pixel = img[r, c]
            for ch in range(3):
                if bit_index < num_bits:
                    val = (val << 1) | (int(pixel[ch]) & 1)
                    bit_index += 1
        return val

    key = read_bits(img, 0, 16)
    length = read_bits(img, 6, 16)

    if length == 0 or length > max_chars:
        raise ValueError("No hidden message found, or image was not encoded with this tool.")

    rng = random.Random(key)
    all_positions = [(r, c) for r in range(h) for c in range(w)
                     if (r * w + c) >= 12]
    
    used = set()
    selected = []
    required_pixels = length * 3
    
    max_attempts = total_pixels * 10
    attempts = 0
    for _ in range(required_pixels):
        while True:
            attempts += 1
            if attempts > max_attempts:
                raise RuntimeError("RNG exhausted — image too small for this message")
            idx = rng.randint(0, len(all_positions) - 1)
            if idx not in used:
                used.add(idx)
                selected.append(all_positions[idx])
                break

    chars = []
    for i in range(length):
        p1 = selected[i * 3]
        p2 = selected[i * 3 + 1]
        p3 = selected[i * 3 + 2]

        val = 0
        pixel1 = img[p1[0], p1[1]]
        val = (val << 1) | (int(pixel1[0]) & 1)
        val = (val << 1) | (int(pixel1[1]) & 1)
        val = (val << 1) | (int(pixel1[2]) & 1)

        pixel2 = img[p2[0], p2[1]]
        val = (val << 1) | (int(pixel2[0]) & 1)
        val = (val << 1) | (int(pixel2[1]) & 1)
        val = (val << 1) | (int(pixel2[2]) & 1)

        pixel3 = img[p3[0], p3[1]]
        val = (val << 1) | (int(pixel3[0]) & 1)
        val = (val << 1) | (int(pixel3[1]) & 1)

        chars.append(chr(val))

    recovered_msg = "".join(chars)
    
    non_printable = 0
    for c in recovered_msg:
        if not (32 <= ord(c) <= 126 or ord(c) in (9, 10, 13)):
            non_printable += 1
            
    if len(recovered_msg) > 0 and non_printable / len(recovered_msg) > 0.2:
        raise ValueError("Could not recover a valid message. Image may not be encoded, or was re-saved as JPG after encoding.")

    return {
        "message": recovered_msg,
        "key": key,
        "length": length
    }
