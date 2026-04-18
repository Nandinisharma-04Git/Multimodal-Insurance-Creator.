import requests
import base64

class HuggingFaceImageError(RuntimeError):
    pass

def generate_insurance_image_data_uri(prompt: str, *, timeout_s: int = 30) -> str:
    """Uses Pollinations.ai - completely free, no API key needed."""
    
    enhanced = (
        f"insurance infographic, {prompt}, "
        "flat design, vector art, shield, umbrella, family, coins, clean modern"
    )
    
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(enhanced)}"
    
    try:
        resp = requests.get(url, timeout=timeout_s)
    except requests.RequestException as e:
        raise HuggingFaceImageError(f"Request failed: {e}")
    
    if resp.status_code >= 400:
        raise HuggingFaceImageError(f"Pollinations error: {resp.status_code}")
    
    b64 = base64.b64encode(resp.content).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"