import os
import replicate
from dotenv import load_dotenv

load_dotenv()

def generate_video(prompt: str, negative_prompt: str = None) -> str:
    """
    Generates a video using the fastest available model for minimal timeout risk.
    """
    print("🚀 Starting FAST video generation...")
    print(f"Prompt: {prompt}")

    # Using correct LTX-Video model reference from fofr
    try:
        print("⚡ Trying LTX-Video (ultra-fast model)...")
        
        output = replicate.run(
            "fofr/ltx-video",  # Correct model reference
            input={
                "prompt": prompt,
                "width": 768,
                "height": 512,
                "num_frames": 121,  # ~5 seconds at 24fps
                "num_inference_steps": 40
            }
        )

        video_url = str(output)
        print(f"✅ LTX-Video generated successfully in record time!")
        print(f"🔗 URL: {video_url}")
        return video_url

    except Exception as e:
        print(f"❌ LTX-Video failed: {e}")
        
        # Fallback to your proven ZeroScope model
        print("🔄 Falling back to reliable ZeroScope model...")
        try:
            fallback_model = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"
            output = replicate.run(
                ref=fallback_model,
                input={"prompt": prompt}
            )
            video_url = str(output[0])
            print(f"✅ Fallback video generated successfully!")
            print(f"🔗 URL: {video_url}")
            return video_url
        except Exception as fallback_error:
            print(f"❌ Both models failed - Fallback error: {fallback_error}")
            return None