from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from video_generator import generate_video
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import threading
import time
from dotenv import load_dotenv
import uuid #new
from datetime import datetime, timedelta #new

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

# In-memory storage for jobs (you can later replace with database)
video_jobs = {} #new

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

# === ADD THESE NEW ROUTES AT THE END OF YOUR EXISTING app.py ===
# (Don't replace anything - just add these routes after your existing routes)

@app.route('/whatsapp/webhook-async', methods=['POST'])
def whatsapp_webhook_async():
    """Safe async webhook - immediate response, background processing"""
    
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    
    print(f"📱 Received WhatsApp message from {from_number}: {incoming_msg}")
    
    resp = MessagingResponse()
    
    try:
        # Handle commands (same as before)
        if incoming_msg.lower().startswith('/help'):
            help_message = """🎬 *AI Video Generator Bot*

Send me a text prompt and I'll create a video for you!

*Commands:*
/help - Show this help message
/status - Check if I'm working
/queue - Check your video queue
/example - See example prompts

*How to use:*
Just send me a description like:
"A cat playing piano in space"
"Sunset over mountains with birds flying"
"A robot dancing in the rain"

*Note:* Videos take 2-3 minutes to generate. I'll send it when ready! 🎥✨"""
            resp.message(help_message)
            
        elif incoming_msg.lower().startswith('/status'):
            resp.message("🟢 *Bot Status: Online*\nSend me a prompt to generate your video!")
            
        elif incoming_msg.lower().startswith('/queue'):
            user_jobs = [job for job in video_jobs.values() if job.get('from_number') == from_number]
            if user_jobs:
                pending = len([job for job in user_jobs if job['status'] == 'pending'])
                processing = len([job for job in user_jobs if job['status'] == 'processing'])
                resp.message(f"📋 *Your Queue:*\n\nPending: {pending}\nProcessing: {processing}\n\nVideos are processed in order. Please wait! ⏳")
            else:
                resp.message("📋 *Your Queue:* Empty\n\nSend a prompt to generate a video!")
                
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
            # Video generation request - QUEUE IT
            job_id = str(uuid.uuid4())[:8]
            
            # Store job in memory (replace with database later)
            video_jobs[job_id] = {
                'job_id': job_id,
                'prompt': incoming_msg,
                'from_number': from_number,
                'to_number': to_number,
                'status': 'pending',
                'created_at': datetime.now(),
                'started_at': None,
                'completed_at': None,
                'error': None
            }
            
            print(f"🎬 Queued video job {job_id} for: {incoming_msg}")
            
            # Immediate response to user
            resp.message(f"🎬 *Video Queued!*\n\nJob ID: `{job_id}`\nPrompt: _{incoming_msg}_\n\n⏳ Your video is in the queue and will be ready in 2-3 minutes. I'll send it automatically when done!\n\nSend `/queue` to check status.")
                    
    except Exception as e:
        print(f"❌ Error processing WhatsApp message: {e}")
        resp.message("😅 Sorry, I encountered an error. Please try again or send /help for assistance.")
    
    return str(resp)

@app.route('/process-video-jobs', methods=['POST'])
def process_video_jobs():
    """External endpoint to process queued jobs - called by external service"""
    
    try:
        # Find oldest pending job
        pending_jobs = [(job_id, job) for job_id, job in video_jobs.items() 
                       if job['status'] == 'pending']
        
        if not pending_jobs:
            return jsonify({'message': 'No pending jobs', 'jobs_processed': 0})
        
        # Sort by creation time and take the oldest
        pending_jobs.sort(key=lambda x: x[1]['created_at'])
        job_id, job = pending_jobs[0]
        
        print(f"🎬 Processing job {job_id}: {job['prompt']}")
        
        # Mark as processing
        video_jobs[job_id]['status'] = 'processing'
        video_jobs[job_id]['started_at'] = datetime.now()
        
        try:
            # Generate video
            negative_prompt = "deformed, distorted, disfigured, poor quality, bad anatomy, ugly, anachronism, blurry, low resolution, noisy, text, watermark, logo"
            video_url = generate_video(job['prompt'], negative_prompt=negative_prompt)
            
            if video_url and twilio_client:
                # Send video to user
                message = twilio_client.messages.create(
                    media_url=[str(video_url)],
                    from_=job['to_number'],
                    to=job['from_number'],
                    body=f"✅ *Your AI Video is Ready!*\n\nPrompt: _{job['prompt']}_\nJob ID: `{job_id}`\n\n🎥 Send another prompt to create more videos!"
                )
                
                # Mark as completed
                video_jobs[job_id]['status'] = 'completed'
                video_jobs[job_id]['completed_at'] = datetime.now()
                
                print(f"✅ Job {job_id} completed and sent to {job['from_number']}")
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'prompt': job['prompt'],
                    'message': 'Video generated and sent successfully'
                })
                
            else:
                # Mark as failed
                video_jobs[job_id]['status'] = 'failed'
                video_jobs[job_id]['error'] = 'Video generation failed'
                video_jobs[job_id]['completed_at'] = datetime.now()
                
                # Send failure message to user
                if twilio_client:
                    twilio_client.messages.create(
                        from_=job['to_number'],
                        to=job['from_number'],
                        body=f"❌ *Video Generation Failed*\n\nJob ID: `{job_id}`\nPrompt: _{job['prompt']}_\n\n😅 Something went wrong. Please try again with a different prompt."
                    )
                
                return jsonify({
                    'success': False,
                    'job_id': job_id,
                    'error': 'Video generation failed'
                })
                
        except Exception as e:
            # Mark as failed
            video_jobs[job_id]['status'] = 'failed'
            video_jobs[job_id]['error'] = str(e)
            video_jobs[job_id]['completed_at'] = datetime.now()
            
            print(f"❌ Job {job_id} failed: {e}")
            
            # Send failure message to user
            if twilio_client:
                twilio_client.messages.create(
                    from_=job['to_number'],
                    to=job['from_number'],
                    body=f"❌ *Video Generation Failed*\n\nJob ID: `{job_id}`\n\n😅 Technical error occurred. Please try again later."
                )
            
            return jsonify({
                'success': False,
                'job_id': job_id,
                'error': str(e)
            })
            
    except Exception as e:
        print(f"❌ Error in job processing: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/jobs', methods=['GET'])
def admin_jobs():
    """Admin endpoint to view all jobs"""
    
    # Clean up old completed jobs (older than 1 hour)
    current_time = datetime.now()
    jobs_to_remove = []
    
    for job_id, job in video_jobs.items():
        if job['status'] in ['completed', 'failed'] and job.get('completed_at'):
            if current_time - job['completed_at'] > timedelta(hours=1):
                jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        del video_jobs[job_id]
    
    # Return job summary
    job_stats = {
        'pending': len([j for j in video_jobs.values() if j['status'] == 'pending']),
        'processing': len([j for j in video_jobs.values() if j['status'] == 'processing']),
        'completed': len([j for j in video_jobs.values() if j['status'] == 'completed']),
        'failed': len([j for j in video_jobs.values() if j['status'] == 'failed']),
        'total': len(video_jobs)
    }
    
    # Recent jobs (last 10)
    recent_jobs = sorted(video_jobs.values(), key=lambda x: x['created_at'], reverse=True)[:10]
    
    return jsonify({
        'stats': job_stats,
        'recent_jobs': [
            {
                'job_id': job['job_id'],
                'prompt': job['prompt'][:50] + '...' if len(job['prompt']) > 50 else job['prompt'],
                'status': job['status'],
                'created_at': job['created_at'].isoformat(),
                'from_number': job['from_number'][-4:]  # Only last 4 digits for privacy
            }
            for job in recent_jobs
        ]
    })

# Optional: Automatic job processor (runs every 30 seconds)
@app.route('/auto-process-jobs', methods=['POST'])
def auto_process_jobs():
    """Auto-process jobs - can be called by external cron service"""
    
    try:
        # Process one job at a time to avoid overloading
        response = process_video_jobs()
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':

    print("🚀 Starting Flask app with WhatsApp bot integration...")
    print(f"📱 WhatsApp webhook will be available at: /whatsapp/webhook")
    print(f"🔍 Bot status check: /whatsapp/status")
    app.run(debug=True, port=5001)