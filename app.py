from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from video_generator import generate_video
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import threading
import time
from dotenv import load_dotenv


load_dotenv()

# The static_folder argument tells Flask where to find CSS, JS, etc.
app = Flask(__name__, static_folder='static')
CORS(app)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio Sandbox number

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None
    print("⚠️  Warning: Twilio credentials not found. WhatsApp functionality will be disabled.")

# In-memory storage for conversation state (in production, use Redis or database)
user_sessions = {}

# === EXISTING ROUTES (UNCHANGED) ===

# This route will serve our main HTML file
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# This route handles requests for any file in the static folder
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# This is our main API endpoint for generating videos (UNCHANGED)
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
            # If successful, return the video URL as JSON
            return jsonify({'video_url': video_url})
        else:
            return jsonify({'error': 'Failed to generate video.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === NEW WHATSAPP ROUTES ===

@app.route('/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio"""
    
    # Get the message details
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    
    print(f"📱 Received WhatsApp message from {from_number}: {incoming_msg}")
    
    # Create TwiML response
    resp = MessagingResponse()
    
    try:
        # Handle different types of messages
        if incoming_msg.lower().startswith('/help'):
            help_message = """🎬 *AI Video Generator Bot*

Send me a text prompt and I'll create a video for you!

*Commands:*
/help - Show this help message
/status - Check if I'm working
/example - See example prompts

*How to use:*
Just send me a description like:
"A cat playing piano in space"
"Sunset over mountains with birds flying"
"A robot dancing in the rain"

*Note:* Video generation takes 15-30 seconds. Please be patient! 🎥✨"""
            resp.message(help_message)
            
        elif incoming_msg.lower().startswith('/status'):
            resp.message("🟢 *Bot Status: Online*\nSend me a prompt to generate your video!")
            
        elif incoming_msg.lower().startswith('/example'):
            example_message = """🎨 *Example Prompts:*

• "A majestic eagle soaring over a mountain range"
• "Children playing in a colorful playground"
• "Ocean waves crashing against rocky cliffs"
• "A futuristic city with flying cars"
• "A peaceful forest with sunlight filtering through trees"

Try one of these or create your own! 🚀"""
            resp.message(example_message)
            
        elif len(incoming_msg) < 10:
            resp.message("🤔 Your prompt seems too short. Try something more descriptive like:\n\n'A sunset over mountains with birds flying'\n\nOr send /help for more examples!")
            
        else:
            # This is a video generation request
            # Send immediate acknowledgment
            resp.message("🎬 *Generating your video...*\n\nThis usually takes 15-30 seconds. I'll send it to you as soon as it's ready! ⏳")
            
            # Store user session
            user_sessions[from_number] = {
                'status': 'generating',
                'prompt': incoming_msg,
                'timestamp': time.time()
            }
            
            # Start video generation in background thread
            thread = threading.Thread(
                target=generate_and_send_video, 
                args=(from_number, to_number, incoming_msg)
            )
            thread.daemon = True
            thread.start()
            
    except Exception as e:
        print(f"❌ Error processing WhatsApp message: {e}")
        resp.message("😅 Sorry, I encountered an error. Please try again or send /help for assistance.")
    
    return str(resp)

def generate_and_send_video(from_number, to_number, prompt):
    """Generate video and send it back to user (runs in background thread)"""
    try:
        print(f"🎬 Starting video generation for: {prompt}")
        
        # Use your existing video generation logic
        negative_prompt = "deformed, distorted, disfigured, poor quality, bad anatomy, ugly, anachronism, blurry, low resolution, noisy, text, watermark, logo"
        video_url = generate_video(prompt, negative_prompt=negative_prompt)
        
        if video_url and twilio_client:
            # Send the video to the user
            message = twilio_client.messages.create(
                media_url=[str(video_url)],
                from_=to_number,
                to=from_number,
                body="✅ *Your AI-generated video is ready!*\n\nSend another prompt to create more videos! 🎥"
            )
            
            print(f"✅ Video sent successfully to {from_number}")
            
            # Update user session
            if from_number in user_sessions:
                user_sessions[from_number]['status'] = 'completed'
                
        else:
            # Send error message
            if twilio_client:
                twilio_client.messages.create(
                    from_=to_number,
                    to=from_number,
                    body="❌ Sorry, I couldn't generate your video. Please try again with a different prompt or send /help for examples."
                )
            print(f"❌ Failed to generate video for prompt: {prompt}")
            
    except Exception as e:
        print(f"❌ Error in video generation thread: {e}")
        
        # Send error message to user
        if twilio_client:
            try:
                twilio_client.messages.create(
                    from_=to_number,
                    to=from_number,
                    body="😅 Something went wrong while generating your video. Please try again or contact support."
                )
            except:
                pass  # Don't fail if we can't send error message

@app.route('/whatsapp/status', methods=['GET'])
def whatsapp_status():
    """Health check endpoint for WhatsApp bot"""
    status = {
        'bot_status': 'online',
        'twilio_configured': bool(twilio_client),
        'active_sessions': len(user_sessions),
        'timestamp': time.time()
    }
    return jsonify(status)

# === UTILITY ENDPOINTS ===

@app.route('/admin/sessions', methods=['GET'])
def get_sessions():
    """Get current user sessions (for debugging)"""
    # Clean old sessions (older than 1 hour)
    current_time = time.time()
    expired_sessions = [
        phone for phone, session in user_sessions.items() 
        if current_time - session.get('timestamp', 0) > 3600
    ]
    
    for phone in expired_sessions:
        del user_sessions[phone]
    
    return jsonify({
        'active_sessions': user_sessions,
        'total_active': len(user_sessions)
    })

if __name__ == '__main__':

    print("🚀 Starting Flask app with WhatsApp bot integration...")
    print(f"📱 WhatsApp webhook will be available at: /whatsapp/webhook")
    print(f"🔍 Bot status check: /whatsapp/status")
    app.run(debug=True, port=5001)