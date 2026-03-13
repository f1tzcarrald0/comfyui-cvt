"""
CVT Vision Analyzer
Analyzes images to extract cinematic parameters using one of 6 model backends:
  - CLIP (local zero-shot classification)
  - Qwen 3 VL 8b (local VLM, auto-downloaded)
  - Gemini (API: gemini-3-flash-preview)
  - ChatGPT (API: gpt-5.2)
  - Claude (API: claude-sonnet-4-6)
  - ChatGPT via ComfyUI (API proxy: uses ComfyUI account credits)
"""

import io
import base64
import json

import torch
import numpy as np
from PIL import Image

# ─────────────────────────────────────────────
#  Analysis prompts per parameter type
# ─────────────────────────────────────────────

ANALYSIS_PROMPTS = {
    "color_grading": (
        "Analyze this image. Describe the color grading, color palette, "
        "and tonal treatment. Note the overall color temperature, contrast, "
        "saturation, and any stylistic color shifts. Be concise (one sentence)."
    ),
    "mood": (
        "Analyze this image. Describe the mood, atmosphere, and emotional "
        "tone conveyed by the composition, lighting, color, and subject matter. "
        "Be concise (one sentence)."
    ),
    "lighting_style": (
        "Analyze this image. Describe the lighting setup, quality, direction, "
        "and character. Note whether it is hard or soft, natural or artificial, "
        "and any notable lighting techniques. Be concise (one sentence)."
    ),
}

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _tensor_to_pil(image_tensor):
    """Convert a ComfyUI IMAGE tensor (B,H,W,3 float32 0-1) to a PIL Image."""
    if image_tensor.dim() == 4:
        image_tensor = image_tensor[0]
    img_np = (image_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(img_np)


def _pil_to_base64(pil_image, max_size=1024):
    """Convert PIL Image to base64-encoded JPEG string, resized if needed."""
    w, h = pil_image.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        pil_image = pil_image.resize(
            (int(w * scale), int(h * scale)), Image.LANCZOS
        )
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ─────────────────────────────────────────────
#  CLIP Backend
# ─────────────────────────────────────────────

_clip_model = None
_clip_processor = None


def _load_clip():
    global _clip_model, _clip_processor
    if _clip_model is not None:
        return
    try:
        from transformers import CLIPModel, CLIPProcessor
    except ImportError:
        raise ImportError(
            "CLIP backend requires the 'transformers' package.\n"
            "Install it with: pip install transformers accelerate"
        )
    print("[CVT] Loading CLIP model (openai/clip-vit-large-patch14-336)...")
    _clip_processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-large-patch14-336"
    )
    _clip_model = CLIPModel.from_pretrained(
        "openai/clip-vit-large-patch14-336"
    )
    _clip_model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _clip_model.to(device)
    print("[CVT] CLIP model loaded.")


def _analyze_clip(pil_image, presets):
    """Zero-shot classify image against preset labels. Returns best match."""
    _load_clip()
    device = next(_clip_model.parameters()).device
    inputs = _clip_processor(
        text=presets, images=pil_image, return_tensors="pt", padding=True
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = _clip_model(**inputs)
    probs = outputs.logits_per_image.softmax(dim=1)
    best_idx = probs.argmax(dim=1).item()
    return presets[best_idx]


# ─────────────────────────────────────────────
#  Qwen 3 VL 8B Backend
# ─────────────────────────────────────────────

_qwen_model = None
_qwen_processor = None


def _load_qwen():
    global _qwen_model, _qwen_processor
    if _qwen_model is not None:
        return
    try:
        from transformers import AutoModelForCausalLM, AutoProcessor
    except ImportError:
        raise ImportError(
            "Qwen backend requires the 'transformers' package.\n"
            "Install it with: pip install transformers accelerate"
        )
    model_id = "Qwen/Qwen3-VL-8B"
    print(f"[CVT] Loading Qwen 3 VL 8B ({model_id})...")
    print("[CVT] This may download several GB on first run.")
    _qwen_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    _qwen_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    _qwen_model.eval()
    print("[CVT] Qwen 3 VL 8B loaded.")


def _analyze_qwen(pil_image, prompt):
    """Run Qwen 3 VL 8B on an image with a text prompt."""
    _load_qwen()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text_input = _qwen_processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _qwen_processor(
        text=[text_input], images=[pil_image], return_tensors="pt", padding=True
    )
    inputs = {k: v.to(_qwen_model.device) for k, v in inputs.items()}
    with torch.no_grad():
        output_ids = _qwen_model.generate(**inputs, max_new_tokens=150)
    # Trim the input tokens from the output
    generated = output_ids[:, inputs["input_ids"].shape[1]:]
    return _qwen_processor.decode(generated[0], skip_special_tokens=True).strip()


# ─────────────────────────────────────────────
#  Gemini API Backend
# ─────────────────────────────────────────────

def _analyze_gemini(b64_image, prompt, api_key):
    """Call Gemini 3 Flash Preview via REST API."""
    import requests

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3-flash-preview:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.3},
    }
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Gemini API error ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response format: {json.dumps(data)[:500]}")


# ─────────────────────────────────────────────
#  ChatGPT API Backend
# ─────────────────────────────────────────────

def _analyze_chatgpt(b64_image, prompt, api_key):
    """Call GPT-5.2 via OpenAI REST API."""
    import requests

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-5.2",
        "max_completion_tokens": 200,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenAI API error ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected OpenAI response format: {json.dumps(data)[:500]}")


# ─────────────────────────────────────────────
#  Claude API Backend
# ─────────────────────────────────────────────

def _analyze_claude(b64_image, prompt, api_key):
    """Call Claude Sonnet 4.6 via Anthropic REST API."""
    import requests

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6-20260220",
        "max_tokens": 200,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    try:
        return data["content"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(
            f"Unexpected Anthropic response format: {json.dumps(data)[:500]}"
        )


# ─────────────────────────────────────────────
#  ChatGPT via ComfyUI API Backend
# ─────────────────────────────────────────────

def _analyze_chatgpt_comfyui(b64_image, prompt, auth_token=None, api_key=None):
    """Call ChatGPT via ComfyUI's API proxy using account credits."""
    import requests

    if not auth_token and not api_key:
        raise RuntimeError(
            "ChatGPT (ComfyUI) requires a ComfyUI account. "
            "Log in to ComfyUI or provide a Comfy API key via "
            "extra_data.api_key_comfy_org in the /prompt payload."
        )

    url = "https://api.comfy.org/proxy/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif api_key:
        headers["X-API-KEY"] = api_key

    payload = {
        "model": "gpt-5",
        "max_completion_tokens": 200,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"ComfyUI API error ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(
            f"Unexpected ComfyUI API response: {json.dumps(data)[:500]}"
        )


# ─────────────────────────────────────────────
#  Public Interface
# ─────────────────────────────────────────────

def analyze_image(image_tensor, parameter_type, model_name, api_key=None, presets=None,
                  comfy_auth_token=None, comfy_api_key=None):
    """
    Analyze an image to extract a cinematic parameter description.

    Args:
        image_tensor: ComfyUI IMAGE tensor (B,H,W,3 float32 0-1)
        parameter_type: One of "color_grading", "mood", "lighting_style"
        model_name: One of "CLIP", "Qwen 3 VL 8b", "Gemini", "ChatGPT", "Claude",
                    "ChatGPT (ComfyUI)"
        api_key: Required for Gemini / ChatGPT / Claude
        presets: List of preset strings (used by CLIP for zero-shot classification)
        comfy_auth_token: ComfyUI session token (for ComfyUI API backends)
        comfy_api_key: ComfyUI account API key (for ComfyUI API backends)

    Returns:
        str: Description or best-matching preset for the parameter.
    """
    if parameter_type not in ANALYSIS_PROMPTS:
        raise ValueError(f"Unknown parameter_type: {parameter_type}")

    prompt = ANALYSIS_PROMPTS[parameter_type]
    pil_image = _tensor_to_pil(image_tensor)

    # ── CLIP ──
    if model_name == "CLIP":
        if not presets:
            raise ValueError("CLIP backend requires a presets list for classification.")
        return _analyze_clip(pil_image, presets)

    # ── Qwen 3 VL 8B ──
    if model_name == "Qwen 3 VL 8b":
        return _analyze_qwen(pil_image, prompt)

    # ── ChatGPT via ComfyUI API (no user API key needed) ──
    if model_name == "ChatGPT (ComfyUI)":
        b64 = _pil_to_base64(pil_image)
        return _analyze_chatgpt_comfyui(b64, prompt, comfy_auth_token, comfy_api_key)

    # ── API-based backends (require user API key) ──
    if not api_key or not api_key.strip():
        raise ValueError(f"API key required for {model_name}. Enter it in the api_key field.")

    b64 = _pil_to_base64(pil_image)

    if model_name == "Gemini":
        return _analyze_gemini(b64, prompt, api_key.strip())

    if model_name == "ChatGPT":
        return _analyze_chatgpt(b64, prompt, api_key.strip())

    if model_name == "Claude":
        return _analyze_claude(b64, prompt, api_key.strip())

    raise ValueError(f"Unknown model_name: {model_name}")


# ─────────────────────────────────────────────
#  Scene Description (free-form prose)
# ─────────────────────────────────────────────

_SCENE_DESCRIBE_PROMPT = (
    "Describe this scene in vivid visual detail for a video prompt. "
    "Include the environment, subjects, objects, textures, colors, lighting, "
    "and spatial relationships. Focus on what a camera would see moving through "
    "this space. Be specific and concise (2-3 sentences, under 60 words)."
)


def describe_scene(image_tensor, model_name, api_key=None,
                   comfy_auth_token=None, comfy_api_key=None):
    """
    Analyze an image and return a free-form prose description of the scene.

    Args:
        image_tensor: ComfyUI IMAGE tensor (B,H,W,3 float32 0-1)
        model_name: One of "Qwen 3 VL 8b", "Gemini", "ChatGPT", "Claude",
                    "ChatGPT (ComfyUI)"
        api_key: Required for Gemini / ChatGPT / Claude
        comfy_auth_token: ComfyUI session token (for ComfyUI API backends)
        comfy_api_key: ComfyUI account API key (for ComfyUI API backends)

    Returns:
        str: Prose description of the scene contents.
    """
    pil_image = _tensor_to_pil(image_tensor)

    if model_name == "Qwen 3 VL 8b":
        return _analyze_qwen(pil_image, _SCENE_DESCRIBE_PROMPT)

    # ChatGPT via ComfyUI API (no user API key needed)
    if model_name == "ChatGPT (ComfyUI)":
        b64 = _pil_to_base64(pil_image)
        return _analyze_chatgpt_comfyui(b64, _SCENE_DESCRIBE_PROMPT, comfy_auth_token, comfy_api_key)

    # API-based backends (require user API key)
    if not api_key or not api_key.strip():
        raise ValueError(f"API key required for {model_name}. Enter it in the api_key field.")

    b64 = _pil_to_base64(pil_image)

    if model_name == "Gemini":
        return _analyze_gemini(b64, _SCENE_DESCRIBE_PROMPT, api_key.strip())

    if model_name == "ChatGPT":
        return _analyze_chatgpt(b64, _SCENE_DESCRIBE_PROMPT, api_key.strip())

    if model_name == "Claude":
        return _analyze_claude(b64, _SCENE_DESCRIBE_PROMPT, api_key.strip())

    raise ValueError(f"Unknown model_name: {model_name}")
