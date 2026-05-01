from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import io
import cv2
from .steg import encode_image, decode_image, _check_image

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "version": "1.0"})

@app.route('/api/image_info', methods=['POST'])
def image_info():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    temp_files = []
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
            return jsonify({'error': 'Invalid file type. Upload PNG, JPG, BMP, or WEBP only.'}), 400

        f = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        temp_files.append(f.name)
        f.close()
        file.save(f.name)

        if os.path.getsize(f.name) < 1024:
            return jsonify({'error': 'File too small to be a valid image.'}), 400
        if os.path.getsize(f.name) > 10 * 1024 * 1024:
            return jsonify({'error': 'Image too large. Maximum 10MB.'}), 400

        img = cv2.imread(f.name, cv2.IMREAD_COLOR)
        h, w, total_pixels, max_chars = _check_image(img, "info")
        
        return jsonify({
            'width': w,
            'height': h,
            'total_pixels': total_pixels,
            'max_message_length': max_chars,
            'format': ext.lstrip('.')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass

@app.route('/api/encode', methods=['POST'])
def encode():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    if 'message' not in request.form:
        return jsonify({'error': 'No message provided'}), 400
        
    file = request.files['image']
    message = request.form['message']
    
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    temp_files = []
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
            return jsonify({'error': 'Invalid file type. Upload PNG, JPG, BMP, or WEBP only.'}), 400

        unique_id = str(uuid.uuid4())
        input_path = os.path.join(tempfile.gettempdir(), f"input_{unique_id}{ext}")
        output_path = os.path.join(tempfile.gettempdir(), f"output_{unique_id}.png")
        temp_files.extend([input_path, output_path])
        
        file.save(input_path)
        
        if os.path.getsize(input_path) < 1024:
            return jsonify({'error': 'File too small to be a valid image.'}), 400
        if os.path.getsize(input_path) > 10 * 1024 * 1024:
            return jsonify({'error': 'Image too large. Maximum 10MB.'}), 400

        key = encode_image(input_path, message, output_path)
        
        with open(output_path, 'rb') as f:
            file_data = f.read()
            
        mem_file = io.BytesIO(file_data)
        response = send_file(mem_file, mimetype='image/png', as_attachment=True, download_name='encoded.png')
        response.headers['X-Steg-Key'] = str(key)
        response.headers['Access-Control-Expose-Headers'] = 'X-Steg-Key'
        
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass


@app.route('/api/decode', methods=['POST'])
def decode():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    temp_files = []
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != '.png':
            return jsonify({'error': 'Decode requires a PNG file. JPG/WEBP will not work as they alter pixel values.'}), 400

        unique_id = str(uuid.uuid4())
        input_path = os.path.join(tempfile.gettempdir(), f"input_{unique_id}.png")
        temp_files.append(input_path)
        
        file.save(input_path)

        if os.path.getsize(input_path) < 1024:
            return jsonify({'error': 'File too small to be a valid image.'}), 400
        if os.path.getsize(input_path) > 10 * 1024 * 1024:
            return jsonify({'error': 'Image too large. Maximum 10MB.'}), 400

        result = decode_image(input_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass

if __name__ == '__main__':
    app.run(debug=True, port=3000)
