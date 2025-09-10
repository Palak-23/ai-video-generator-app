import requests
import os

# --- IMPORTANT: VERCEL ENVIRONMENT VARIABLES ---
# You must set these in your Vercel project's settings.
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_video_to_whatsapp(user_wa_id, video_url, prompt):
    """
    Sends a video message to a WhatsApp user via the Twilio API.
    This function should be called from your existing backend after video generation.

    Args:
        user_wa_id (str): The WhatsApp ID of the user (their phone number).
        video_url (str): A publicly accessible URL to the generated video file.
        prompt (str): The original prompt from the user.
    """
    url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"
    
    auth = (ACCOUNT_SID, AUTH_TOKEN)
    
    data = {
        'From': TWILIO_PHONE_NUMBER,
        'To': f'whatsapp:{user_wa_id}',
        'Body': f"Here's your video for: '{prompt}'!",
        'MediaUrl': [video_url]
    }
    
    try:
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Video sent successfully to {user_wa_id}.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send video to {user_wa_id}: {e}")
        return False
