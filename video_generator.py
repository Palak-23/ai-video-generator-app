import os
import replicate
from dotenv import load_dotenv

load_dotenv()

def generate_video(prompt: str, negative_prompt: str = None) -> str:
    """
    Generates a video with the absolute minimum parameters for debugging.
    """
    print("🚀 Starting BARE MINIMUM video generation test...")
    print(f"Prompt: {prompt}")

    model_version = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

    try:
        # We are only sending the prompt. Nothing else.
        output = replicate.run(
            ref=model_version,
            input={"prompt": prompt}
        )

        video_url = str(output[0]) 
        print(f"✅ Video generated successfully!")
        print(f"🔗 URL: {video_url}")
        return video_url

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None