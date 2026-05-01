

---

```
Build a full-stack image steganography web application in Python, deployable on Vercel.
The app lets users hide secret messages inside images using LSB (Least Significant Bit)
substitution. Read every instruction carefully before writing any code.

---

## WHAT THE APP DOES

ENCODING:
1. User uploads any image (PNG, JPG, BMP, WEBP)
2. User types a secret message
3. App generates a random 16-bit key (0-65535)
4. Key (16 bits) is stored in the LSBs of the first 6 pixels, BGR channels, row 0
5. Message length (16 bits) is stored in LSBs of pixels 6-11, row 0
6. Key seeds a random number generator that selects unique pixels for each character
7. Each character's 8 ASCII bits are written into LSBs of BGR channels of its assigned pixel
8. Output is saved as PNG (lossless — critical, JPEG would destroy LSB data)
9. User downloads the output PNG — looks identical to original

DECODING:
1. User uploads the encoded PNG
2. App reads pixels 0-5 row 0 to recover key
3. Reads pixels 6-11 row 0 to recover message length
4. Seeds same RNG with recovered key
5. Regenerates identical pixel selection
6. Reads LSBs from those pixels, reconstructs ASCII characters
7. Returns the hidden message

---

## STEP 1 — Core Python Logic

Create api/steg.py with these two functions:

### encode_image(input_path, message, output_path)

```
python
import cv2
import numpy as np
import random

def encode_image(input_path, message, output_path):
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError("Cannot open image")

    h, w = img.shape[:2]
    total_pixels = h * w
    max_message_len = total_pixels - 12  # first 12 pixels reserved for metadata
    
    if len(message) > max_message_len:
        raise ValueError(f"Message too long. Max {max_message_len} characters for this image.")

    key = random.randint(0, 65535)
    length = len(message)

    # Store key in pixels 0-5, row 0 (16 bits across 3 channels x 6 pixels = 18 slots)
    def store_bits(img, start_col, value, num_bits):
        bit_index = 0
        for c in range(start_col, w):
            pixel = img[0, c].copy()
            for ch in range(3):
                if bit_index < num_bits:
                    bit = (value >> (num_bits - 1 - bit_index)) & 1
                    pixel[ch] = (int(pixel[ch]) & 0xFE) | bit
                    bit_index += 1
            img[0, c] = pixel
            if bit_index >= num_bits:
                break

    store_bits(img, 0, key, 16)
    store_bits(img, 6, length, 16)

    # Pseudorandom pixel selection (exclude row 0 cols 0-11)
    rng = random.Random(key)
    all_positions = [(r, c) for r in range(h) for c in range(w)
                     if not (r == 0 and c < 12)]
    
    used = set()
    selected = []
    for _ in range(length):
        while True:
            idx = rng.randint(0, len(all_positions) - 1)
            if idx not in used:
                used.add(idx)
                selected.append(all_positions[idx])
                break

    # Embed each character
    for i, ch_char in enumerate(message):
        data = ord(ch_char)
        r, c = selected[i]
        pixel = img[r, c].copy()
        for bit_pos in range(8):
            ch = bit_pos % 3
            bit = (data >> (7 - bit_pos)) & 1
            pixel[ch] = (int(pixel[ch]) & 0xFE) | bit
            if bit_pos == 2:
                img[r, c] = pixel
                # move to next pixel if needed
        img[r, c] = pixel

    # Save as PNG (lossless)
    cv2.imwrite(output_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    return key
```

IMPORTANT: The pixel embedding logic above is a starting sketch.
Rewrite it properly so that 8 bits per character are stored cleanly:
- bits 0,1,2 go into B,G,R channels of pixel at selected[i]
- bits 3,4,5 go into B,G,R channels of the NEXT consecutive pixel
- bits 6,7 go into B,G channels of the pixel after that
- This means each character uses ceil(8/3) = 3 pixels
- selected[] must therefore contain enough unique pixel positions (length * 3 positions minimum)
- Make sure the decode function mirrors this exactly

### decode_image(input_path)

Mirror of encode — read bits back from the same positions in the same order.
Return: { message, key, length }

---

## STEP 2 — Flask API

Create api/index.py as a Vercel serverless function.

Endpoints:

POST /api/encode
- Accepts: multipart form with 'image' file and 'message' text field
- Validates: file is image, message not empty, message not too long for image
- Runs encode_image()
- Returns encoded PNG as downloadable file with header:
  X-Steg-Key: <key>
- Clean up all temp files in finally block

POST /api/decode  
- Accepts: multipart form with 'image' file (must be PNG)
- Runs decode_image()
- Returns JSON: { message, key, length }
- Clean up all temp files in finally block

POST /api/image_info
- Accepts: image file
- Returns JSON: { width, height, total_pixels, max_message_length, format }

GET /api/health
- Returns: { status: "ok", version: "1.0" }

Error handling: always return JSON { error: "message" } with appropriate HTTP status code.
Never let an unhandled exception crash the function — wrap everything in try/except.

---

## STEP 3 — Frontend (public/index.html)

Single HTML file. No build step. No npm. Pure HTML + CSS + JS only.
Load fonts and any libraries from CDN only.

### VISUAL THEME — FUTURISTIC LIGHT

Aesthetic: Clean, clinical, high-tech laboratory. Think CERN control room meets 
Apple product page. Light themed but not boring — sharp, precise, intentional.

- Background: #f0f4ff (very light blue-white)
- Surface cards: pure white with subtle drop shadows
- Primary accent: #0047ff (electric blue)
- Secondary accent: #00d4aa (cyan-teal)
- Text: #0a0a1a (near black)
- Borders: 1px solid rgba(0,71,255,0.15)
- Font: 'Syne' for headings (from Google Fonts), 'DM Mono' for code/keys/values
- Corner radius: sharp — 4px or 6px max. Not rounded pill buttons.
- Shadows: blue-tinted — box-shadow: 0 4px 24px rgba(0,71,255,0.08)

Animations required:
1. Page load — panels slide up with staggered delay (CSS animation)
2. Hero title — each letter animates in with a slight vertical offset
3. Upload drop zone — dashed animated border that rotates/pulses when dragging
4. Encoding progress — horizontal progress bar with shimmer animation
5. Key reveal — the generated key types itself out character by character (JS)
6. Decoded message reveal — typewriter effect, character by character
7. Hover on buttons — subtle upward translate + shadow intensify
8. Background — very subtle animated mesh gradient (CSS @keyframes hue-rotate on a 
   radial gradient, slow 8s loop, barely perceptible)

### LAYOUT

Header:
  - Logo mark (geometric diamond SVG icon, blue)
  - "PIXELVAULT" wordmark in Syne font
  - Tagline: "Lossless Image Steganography"
  - Small status pill top-right: "● SYSTEM READY" in green

Two column layout below header (stack on mobile):

LEFT COLUMN — ENCODE PANEL:
  Title: "ENCODE" with small "01" label top right of panel
  
  Step 1 — Image upload:
    Drop zone with dashed blue border
    Shows image preview thumbnail after upload (use FileReader)
    Shows image dimensions and max message capacity below preview
  
  Step 2 — Message input:
    Textarea with monospace font
    Live character counter: "23 / 48420 characters"
    Capacity bar (thin progress bar showing % of image used)
  
  Step 3 — Encode:
    Button: "ENCODE IMAGE" — full width, electric blue, sharp corners
    Progress state: shows shimmer bar during processing
    
  Result state (shown after success):
    Generated key display:
      Label: "ENCRYPTION KEY"
      Value in DM Mono, large, blue — e.g. "47291"
      Copy button next to it
      Warning text: "Key is embedded in image. No need to share separately."
    Download button: "DOWNLOAD ENCODED IMAGE" — outlined style

RIGHT COLUMN — DECODE PANEL:
  Title: "DECODE" with small "10" label top right of panel
  
  Upload zone for encoded PNG
  Button: "DECODE IMAGE"
  
  Result state:
    Panel slides in from below
    Label: "RECOVERED MESSAGE"
    Message text reveals with typewriter effect
    Metadata below in small monospace: Key: XXXXX | Length: XX chars

Bottom section — HOW IT WORKS:
  Three cards in a row explaining LSB, Key Storage, Lossless Output
  Each card has a small geometric icon (SVG), title, 2-line explanation
  Clean, minimal, no clutter

Footer:
  "Built with Python + OpenCV · LSB Steganography · PNG Lossless Output"

---

## STEP 4 — File Structure

/
├── api/
│   ├── index.py       # Flask serverless entrypoint
│   └── steg.py        # encode_image and decode_image functions
├── public/
│   └── index.html     # complete frontend
├── vercel.json
└── requirements.txt

vercel.json:
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "public/**", "use": "@vercel/static" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*)", "dest": "/public/$1" }
  ]
}

requirements.txt:
flask
opencv-python-headless
numpy
Pillow

---

## STEP 5 — CRITICAL RULES

1. PNG ONLY for output. Never JPEG. JPEG is lossy and destroys LSB data.
   Use cv2.imwrite with [cv2.IMWRITE_PNG_COMPRESSION, 0] (compression 0 = no compression,
   maximum speed, still lossless).

2. Input images: accept PNG, JPG, JPEG, BMP, WEBP. Convert to PNG internally before processing.
   When reading a JPG input, convert it to PNG first (cv2.imread then cv2.imwrite as PNG)
   before embedding, because the original JPG pixels are what matter for steganography.

3. Temp files: use Python's tempfile module. Always delete in finally blocks.

4. Vercel limits: 4.5MB response limit, 10s timeout (hobby). Warn user if image is large.
   For images under 2MB this should work fine. Display a warning for larger images.

5. The encode and decode logic must be exactly symmetrical. Write both functions,
   then manually trace through a simple example ("Hi") to verify they produce the same result.

6. No external state. Each API call is stateless. No database. No session storage.

7. Frontend: the encoded image must be downloaded directly from the /api/encode response
   (as a file blob). Use fetch() with response.blob() then create a download link dynamically.
   The key should be extracted from the X-Steg-Key response header.

8. Mobile responsive. The two-column layout collapses to single column below 768px.

9. After writing all code, run a self-check:
   - Does encode → decode round trip work for "Hello World"?
   - Is the output always PNG?
   - Are all temp files cleaned up?
   - Do all API endpoints return JSON errors (never HTML error pages)?
   - Does the frontend handle network errors gracefully?

---
Great question. Here are all the ways it can break and the checks needed. Add this entire section to your prompt:

---

```
## STEP 6 — BULLETPROOFING (read this carefully, implement every check)

### INPUT VALIDATION — IMAGE UPLOAD (encode)

1. FILE TYPE CHECK
   - Accept only: PNG, JPG, JPEG, BMP, WEBP
   - Check BOTH the file extension AND the actual file magic bytes
   - Do not trust the filename alone — check the first 8 bytes of the file
   - If mismatch: return { error: "Invalid file type. Upload PNG, JPG, BMP, or WEBP only." }

2. FILE SIZE CHECK
   - Reject files over 10MB before even reading them
   - If too large: return { error: "Image too large. Maximum 10MB." }
   - Reject files under 1KB — too small to be a real image
   - If too small: return { error: "File too small to be a valid image." }

3. IMAGE DIMENSIONS CHECK
   - After cv2.imread(), check img is not None
   - If None: return { error: "Could not read image. File may be corrupted." }
   - Minimum image size: 10 pixels wide AND 10 pixels tall
   - If smaller: return { error: "Image too small. Minimum 10x10 pixels." }
   - Check that total_pixels > 12 (need at least 12 pixels for metadata storage)

4. CAPACITY CHECK
   - Each character needs 3 pixels (8 bits split across BGR channels)
   - Metadata uses 12 pixels (pixels 0-11 of row 0)
   - usable_pixels = total_pixels - 12
   - max_chars = usable_pixels // 3
   - If message length > max_chars: return error with exact limit
   - Example: a 100x100 image = 10000 pixels, max_chars = (10000-12)//3 = 3329 chars
   - A tiny 10x10 image = 100 pixels, max_chars = (100-12)//3 = 29 chars
   - ALWAYS calculate and return max_chars in /api/image_info response

5. EMPTY MESSAGE CHECK
   - If message is empty string or whitespace only: return error
   - Strip whitespace before length check but preserve original for embedding

6. MESSAGE CHARACTER CHECK
   - Only standard ASCII (0-127) is supported
   - Check every character: if ord(char) > 127 raise error
   - Return: { error: "Message contains unsupported characters. Use ASCII only (no emoji or special symbols)." }
   - Show which character caused the issue if possible

7. PIXEL POSITION COLLISION CHECK
   - When generating random pixel positions, the RNG must never run out of unique positions
   - Required unique pixels = length * 3 (3 pixels per character) + 12 (metadata)
   - If required > total_pixels: return capacity error BEFORE running RNG
   - The RNG loop must have a maximum iteration guard:
     max_attempts = total_pixels * 10
     attempts = 0
     while idx in used:
         idx = rng.randint(...)
         attempts += 1
         if attempts > max_attempts:
             raise RuntimeError("RNG exhausted — image too small for this message")

---

### INPUT VALIDATION — IMAGE UPLOAD (decode)

1. Must be PNG only — JPG decode will always fail because JPG recompressed the pixels
   - Check file extension AND magic bytes for PNG signature: b'\x89PNG'
   - If not PNG: return { error: "Decode requires a PNG file. JPG/WEBP will not work as they alter pixel values." }

2. Check img dimensions after imread — same as encode

3. After reading key and length from frame 0:
   - key must be 0-65535
   - length must be > 0
   - length must be < max_chars for this image
   - If length is 0 or absurdly large: 
     return { error: "No hidden message found, or image was not encoded with this tool." }
   - This catches the case where someone uploads a non-encoded PNG

4. After decoding characters, validate them:
   - Every recovered char must be printable ASCII (32-126) or common whitespace (9, 10, 13)
   - If more than 20% of chars are non-printable: image was probably not encoded with this tool
   - Return: { error: "Could not recover a valid message. Image may not be encoded, or was re-saved as JPG after encoding." }

---

### RUNTIME ERROR HANDLING

1. cv2.imread returns None silently — always check:
   img = cv2.imread(path)
   if img is None:
       raise ValueError("OpenCV could not open the image")

2. cv2.imwrite can fail silently — always check return value:
   success = cv2.imwrite(output_path, img, [...])
   if not success:
       raise RuntimeError("Failed to write output PNG")

3. Temp file cleanup — use this pattern for EVERY endpoint:
   temp_files = []
   try:
       f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
       temp_files.append(f.name)
       ...
   except Exception as e:
       return jsonify({'error': str(e)}), 500
   finally:
       for path in temp_files:
           try:
               if os.path.exists(path):
                   os.remove(path)
           except:
               pass

4. Vercel /tmp space — Vercel gives 512MB of /tmp but it is shared across 
   concurrent requests. Always use unique filenames:
   import uuid
   unique_id = str(uuid.uuid4())
   input_path = f"/tmp/input_{unique_id}.png"

5. Memory — very large images (8000x8000+) loaded into numpy can use 
   hundreds of MB. Add a pixel count limit:
   if h * w > 25_000_000:  # 25 megapixels
       return { error: "Image too large. Maximum 25 megapixels." }

6. Timeout guard — Vercel times out at 10s. Encoding a 25MP image 
   takes too long. Recommended limits:
   - Encode: max 8MP (e.g. 2828x2828) — takes ~3-4s
   - Decode: max 8MP — faster since we only read specific pixels
   - Return clear error if over limit

---

### FRONTEND VALIDATION (never trust backend alone)

Do all these checks IN THE BROWSER before sending the request:

1. Before encode:
   - File selected? If not: show inline error "Please upload an image"
   - File type valid? Check file.type
   - File size under 10MB? Check file.size
   - Message not empty? Check trimmed length
   - Message characters all ASCII? 
     for (let c of message) { if (c.charCodeAt(0) > 127) { show error } }
   - Message length vs capacity: call /api/image_info first when image is selected,
     get max_chars, check message.length <= max_chars BEFORE submitting
     Show live feedback: "Your message uses X of Y available characters"

2. Before decode:
   - File selected? 
   - File is PNG? Check file.name.endsWith('.png') and file.type === 'image/png'
   - Show warning: "Only PNG files can be decoded. JPG files will not work."

3. Network errors:
   - Wrap every fetch() in try/catch
   - Handle response.ok === false: show response JSON error message
   - Handle fetch rejection (no network): show "Connection failed. Check your internet."
   - Always re-enable buttons after request completes (success or failure)
   - Never leave the UI in a loading state permanently

4. Image preview validation:
   - When image loads in FileReader, check naturalWidth and naturalHeight
   - If either is 0: "Image could not be previewed — file may be corrupted"

---

### EDGE CASES TO HANDLE

1. User uploads an already-encoded image to the encode panel again
   - This works fine — steganography is additive as long as capacity allows
   - No special handling needed

2. User uploads a decoded image (the output PNG) and tries to decode again
   - Will decode the original message again correctly — this is fine
   - No special handling needed

3. User re-saves the PNG as JPG outside the app then tries to decode
   - Will fail — make this clear in UI
   - Add a visible warning after download: "Do not convert or re-save this file. 
     Converting to JPG will permanently destroy the hidden message."

4. Message with newlines and spaces
   - Must work — preserve all whitespace in embedding
   - Newline = ASCII 10, Space = ASCII 32, both valid

5. Single character message
   - Must work — minimum 3 pixels needed (1 char x 3 pixels)
   - Covered by capacity check

6. Message exactly at capacity limit
   - Must work — test this explicitly

7. Zero-byte file upload
   - Caught by file size < 1KB check

8. Corrupted PNG (valid extension, invalid data)
   - cv2.imread returns None — caught by None check

9. Extremely wide image (1x10000)
   - Works fine as long as total pixel count is sufficient
   - No special handling needed

10. Grayscale image uploaded
    - cv2.imread reads as 3-channel BGR by default (converts grayscale to BGR)
    - Works fine — no special handling needed

11. Image with alpha channel (RGBA PNG)
    - Use cv2.imread(path, cv2.IMREAD_COLOR) to force 3-channel BGR
    - Drop alpha channel — only use B, G, R for embedding
    - Output PNG will not have alpha channel (fine for steganography)

12. Concurrent users on Vercel
    - All temp files use uuid in filename — no collision possible
    - Each request is completely independent

---

### ERROR MESSAGE STANDARDS

Every error returned by the API must:
- Be in JSON format: { "error": "Human readable message" }
- Use plain English — no Python tracebacks, no technical jargon
- Be specific — not "Something went wrong" but "Image too small. Need at least 40 pixels for a 10-character message."
- Include the limit when relevant — "Message too long. Max 3329 characters for this image."

Every error shown in the UI must:
- Appear inline near the relevant input — not just console.log
- Be dismissible
- Not persist after the user fixes the issue
- Be styled in red/warning color with an icon

---

### SELF TEST CHECKLIST

Before finishing, run these tests mentally or actually:

[ ] 10x10 image + 1 char message → should encode and decode successfully
[ ] 10x10 image + 30 char message → should fail with capacity error
[ ] 100x100 image + "Hello World" → encode then decode → exact match
[ ] Upload JPG to decode endpoint → should return clear error
[ ] Upload non-image file (PDF renamed to PNG) → should return clear error  
[ ] Empty message → should return clear error
[ ] Message with emoji (🔒) → should return clear error
[ ] Message exactly at capacity → should encode successfully
[ ] Message at capacity + 1 char → should fail with capacity error
[ ] Very large image (4000x3000) → should encode in under 10 seconds
[ ] Corrupted PNG (random bytes) → should return clear error, not crash
```

---


## DELIVERABLES

When complete, provide:
1. All files listed in the project structure above
2. Exact Vercel deployment commands
3. Confirmation of successful encode/decode round trip test
4. Any known limitations (file size, character support, etc.)
```

---

