from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from video_generator import generate_video
from video_sender import send_video_to_whatsapp
from threading import Thread

# The static_folder argument tells Flask where to find CSS, JS, etc.
app = Flask(__name__, static_folder='static')
CORS(app)

# This route will serve our main HTML file
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# This route handles requests for any file in the static folder
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

def generate_and_send_video(prompt, user_wa_id, negative_prompt):
    """
    Generates the video and sends it to WhatsApp in a non-blocking thread.
    """
    try:
        video_url = generate_video(prompt, negative_prompt=negative_prompt)
        video_url = str(video_url)

        if video_url:
            send_video_to_whatsapp(user_wa_id, video_url, prompt)
        else:
            send_video_to_whatsapp(user_wa_id, "Sorry, I failed to generate your video.", prompt)
    except Exception as e:
        send_video_to_whatsapp(user_wa_id, f"An error occurred: {str(e)}", prompt)

# This is the new API endpoint for our WhatsApp bot.
@app.route('/generate-video', methods=['POST'])
def handle_whatsapp_generation():
    data = request.get_json()
    if not data or 'prompt' not in data or 'user_id' not in data:
        return jsonify({'error': 'Invalid payload.'}), 400
    
    prompt = data['prompt']
    user_wa_id = data['user_id']
    negative_prompt = "deformed, distorted, disfigured, poor quality, bad anatomy, ugly, anachronism, blurry, low resolution, noisy, text, watermark, logo"

    # Start video generation in a separate thread to prevent timeouts.
    thread = Thread(target=generate_and_send_video, args=(prompt, user_wa_id, negative_prompt))
    thread.start()

    return jsonify({'status': 'Video generation started.'}), 202

# This is our original API endpoint for the web app.
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
        video_url = str(video_url)
        
        if video_url:
            return jsonify({'video_url': video_url})
        else:
            return jsonify({'error': 'Failed to generate video.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
