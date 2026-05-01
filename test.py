import cv2
import numpy as np
import os
from api.steg import encode_image, decode_image

def test():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:,:] = (255, 255, 255) # white image
    cv2.imwrite("test_input.png", img)
    
    msg = "Hello World! This is a test."
    print("Testing encode...")
    key = encode_image("test_input.png", msg, "test_encoded.png")
    print(f"Encoded with key: {key}")
    
    print("Testing decode...")
    result = decode_image("test_encoded.png")
    print(f"Recovered key: {result['key']}")
    print(f"Recovered msg: {result['message']}")
    
    if result['message'] == msg:
        print("TEST PASSED: Messages match!")
    else:
        print("TEST FAILED: Messages don't match.")
        
    os.remove("test_input.png")
    os.remove("test_encoded.png")

if __name__ == "__main__":
    test()
