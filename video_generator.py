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

    # Using LTX-Video - fastest model available (completes in ~44 seconds)
    model_version = "lightricks/ltx-video:06f05417d7503beaeb59c4b2f84b8ef19a0e22b02cd5eca36a7c8e91dcaeb2ad"

    try:
        # Minimal parameters for fastest generation
        output = replicate.run(
            ref=model_version,
            input={
                "prompt": prompt,
                "duration": "5s",  # Shorter videos generate faster
                "aspect_ratio": "16:9"
            }
        )

        video_url = str(output)

        print(f"✅ Video generated successfully!")
        print(f"🔗 URL: {video_url}")
        return video_url

    except Exception as e:
        print(f"❌ An error occurred with LTX-Video: {e}")
        
        # Fallback to your current working model
        print("🔄 Falling back to ZeroScope...")
        try:
            fallback_model = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"
            output = replicate.run(
                ref=fallback_model,
                input={"prompt": prompt}
            )
            video_url = str(output[0])
            print(f"✅ Fallback video generated successfully!")
            return video_url
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return None

# import os
# import replicate
# from dotenv import load_dotenv

# load_dotenv()

# def generate_video(prompt: str, negative_prompt: str = None) -> str:
#     """
#     Generates a video with the absolute minimum parameters for debugging.
#     """
#     print("🚀 Starting BARE MINIMUM video generation test...")
#     print(f"Prompt: {prompt}")

#     model_version = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

#     try:
#         # We are only sending the prompt. Nothing else.
#         output = replicate.run(
#             ref=model_version,
#             input={"prompt": prompt}
#         )

#         video_url = str(output[0]) 
#         print(f"✅ Video generated successfully!")
#         print(f"🔗 URL: {video_url}")
#         return video_url

#     except Exception as e:
#         print(f"❌ An error occurred: {e}")
#         return None