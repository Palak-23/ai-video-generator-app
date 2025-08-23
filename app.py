from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from video_generator import generate_video

# The static_folder argument tells Flask where to find CSS, JS, etc.
app = Flask(__name__, static_folder='static')
CORS(app)

# This route will serve our main HTML file
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# --- ADD THIS NEW ROUTE ---
# This route handles requests for any file in the static folder
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)
# --- END OF ADDITION ---

# This is our main API endpoint for generating videos
@app.route('/generate', methods=['POST'])
def handle_generation():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'No prompt provided.'}), 400

    prompt = data['prompt']
    negative_prompt = "deformed, distorted, disfigured, poor quality, bad anatomy, ugly, anachronism, blurry, low resolution, noisy, text, watermark, logo"

    try:
        # Call our existing function to generate the video
        video_url = generate_video(prompt, negative_prompt=negative_prompt)

        # --- ADD THIS CHECK --- 
        # Although the change is in generate_video, this makes the app more robust
        video_url = str(video_url) 

        if video_url:
            # If successful, return the video URL as JSON
            return jsonify({'video_url': video_url})
        else:
            return jsonify({'error': 'Failed to generate video.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)