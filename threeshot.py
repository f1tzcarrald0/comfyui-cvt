"""
ComfyUI Custom Node: ThreeShot
Assembles a 1–3 shot video prompt for Sora with per-shot camera, lighting,
color, mood, and action controls. Supports image-driven parameter
extraction via CLIP, Qwen 3 VL, Gemini, ChatGPT, or Claude.

Outputs a single Sora-ready video prompt.
"""

from .presets import (
    CAMERA_MOTIONS,
    CAMERA_SHOT_TYPES,
    COLOR_GRADING_PRESETS,
    MOOD_PRESETS,
    LIGHTING_STYLES,
)

ANALYSIS_MODELS = ["none", "CLIP", "Qwen 3 VL 8b", "Gemini", "ChatGPT", "Claude", "ChatGPT (ComfyUI)"]


# ─────────────────────────────────────────────
#  FlexibleDict — accepts dynamic image inputs from JS
# ─────────────────────────────────────────────

class FlexibleDict(dict):
    """Dict subclass where __contains__ and __getitem__ accept any key.
    This lets ComfyUI accept dynamically-added image inputs from the
    frontend JS without requiring them in the static INPUT_TYPES definition.
    Explicitly-defined keys return their real type specs; unknown keys
    return ("*",) so ComfyUI treats them as wildcard-typed inputs.
    """
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            # Dynamic image inputs added by JS — accept any type
            return ("*",)


# Maps the image-toggleable parameter keys to their preset lists
# and the corresponding kwarg suffix used for image inputs.
_IMAGE_PARAMS = {
    "color_grading": {"presets": COLOR_GRADING_PRESETS,   "image_key": "image_color_grading"},
    "mood":          {"presets": MOOD_PRESETS,            "image_key": "image_mood"},
    "lighting_style":{"presets": LIGHTING_STYLES,         "image_key": "image_lighting"},
}


# ─────────────────────────────────────────────
#  ThreeShot Node
# ─────────────────────────────────────────────

class ThreeShot:
    """Builds a 1–3 shot Sora video prompt from structured cinematic parameters."""

    @classmethod
    def INPUT_TYPES(cls):
        required = {}

        # ── Global settings ──
        # Widget order matters — ComfyUI renders them top-to-bottom
        required["shot_count"] = (["1", "2", "3"], {
            "default": "3",
            "tooltip": "Number of shots in the sequence (1, 2, or 3).",
        })
        required["analysis_model"] = (ANALYSIS_MODELS, {
            "default": "ChatGPT",
            "tooltip": "Vision model for image-driven parameters. Select 'none' to disable.",
        })
        required["api_key"] = ("STRING", {
            "default": "",
            "tooltip": "API key for Gemini, ChatGPT, or Claude vision analysis.",
        })
        required["style_prompt"] = ("STRING", {
            "multiline": True,
            "default": "",
            "tooltip": "Overall visual style, mood, genre, or aesthetic that applies to all shots.",
        })
        required["enable_subject_description"] = ("BOOLEAN", {
            "default": False,
            "tooltip": "Enable the subject description field to lock subject appearance across shots.",
        })
        required["subject_description"] = ("STRING", {
            "multiline": True,
            "default": "",
            "tooltip": "Locked subject appearance description carried across all shots.",
        })

        # ── Per-shot parameters (×3) ──
        for n in range(1, 4):
            required[f"shot_{n}_prompt"] = ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": f"What happens in shot {n} — subject, action, emotion, key details.",
            })
            required[f"shot_{n}_camera_motion"] = (CAMERA_MOTIONS, {
                "tooltip": f"Shot {n}: Camera movement during the shot.",
            })
            required[f"shot_{n}_shot_type"] = (CAMERA_SHOT_TYPES, {
                "tooltip": f"Shot {n}: Framing / camera angle.",
            })
            required[f"shot_{n}_color_grading"] = (COLOR_GRADING_PRESETS, {
                "tooltip": f"Shot {n}: Color grading style.",
            })
            required[f"shot_{n}_mood"] = (MOOD_PRESETS, {
                "tooltip": f"Shot {n}: Mood / atmosphere.",
            })
            required[f"shot_{n}_lighting_style"] = (LIGHTING_STYLES, {
                "tooltip": f"Shot {n}: Lighting style.",
            })

            # Image-mode toggles
            required[f"shot_{n}_use_image_color_grading"] = ("BOOLEAN", {
                "default": True,
                "tooltip": f"Shot {n}: Use an input image to determine color grading instead of the dropdown.",
            })
            required[f"shot_{n}_use_image_mood"] = ("BOOLEAN", {
                "default": True,
                "tooltip": f"Shot {n}: Use an input image to determine mood instead of the dropdown.",
            })
            required[f"shot_{n}_use_image_lighting"] = ("BOOLEAN", {
                "default": True,
                "tooltip": f"Shot {n}: Use an input image to determine lighting style instead of the dropdown.",
            })

        # ── Optional (FlexibleDict accepts dynamic image inputs from JS) ──
        optional = FlexibleDict({})

        return {
            "required": required,
            "optional": optional,
            "hidden": {
                "auth_token_comfy_org": "AUTH_TOKEN_COMFY_ORG",
                "api_key_comfy_org": "API_KEY_COMFY_ORG",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_prompt",)
    FUNCTION = "build"
    CATEGORY = "SoraUtils"
    OUTPUT_NODE = False

    # ── Format a single shot as a Sora-ready prose paragraph ──

    def _format_shot_prose(self, prompt, camera_motion, shot_type,
                           color_grading, mood, lighting_style,
                           subject_description=""):
        """Build a Sora 2 optimized video prompt block for one shot.

        Format: rich prose scene description (front-loaded with the most
        important visual details) followed by structured cinematography,
        lighting, and color-palette blocks.  Targets the 80–150 word
        sweet spot that Sora 2 responds to best.
        """
        lines = []

        # ── Scene prose ──
        # Sora 2 best practice: place primary visual content in the
        # first ~500 characters so the model locks on early.
        scene_parts = []
        if subject_description and subject_description.strip():
            scene_parts.append(subject_description.strip().rstrip(".") + ".")
        if prompt and prompt.strip():
            scene_parts.append(prompt.strip())
        scene_parts.append(f"The atmosphere is {mood}.")
        lines.append(" ".join(scene_parts))

        # ── Cinematography (structured block) ──
        lines.append(
            f"Cinematography: {shot_type} framing. "
            f"Camera movement: {camera_motion}."
        )

        # ── Lighting ──
        lines.append(f"Lighting: {lighting_style}.")

        # ── Color palette ──
        lines.append(f"Color palette: {color_grading}.")

        return "\n".join(lines)

    # ── Resolve a parameter value (dropdown or image analysis) ──

    def _resolve_param(self, param_key, dropdown_value, use_image, shot_n,
                       analysis_model, api_key, kwargs,
                       comfy_auth_token=None, comfy_api_key=None):
        """Return the final string for a parameter — either from the dropdown or image analysis."""
        if not use_image or analysis_model == "none":
            return dropdown_value

        info = _IMAGE_PARAMS.get(param_key)
        if not info:
            return dropdown_value

        image_kwarg = f"shot_{shot_n}_{info['image_key']}"
        image_tensor = kwargs.get(image_kwarg)

        if image_tensor is None:
            # Toggle is on but no image connected — fall back to dropdown
            return dropdown_value

        # Lazy import to avoid loading vision_analyzer at startup
        from .vision_analyzer import analyze_image

        return analyze_image(
            image_tensor=image_tensor,
            parameter_type=param_key,
            model_name=analysis_model,
            api_key=api_key,
            presets=info["presets"],
            comfy_auth_token=comfy_auth_token,
            comfy_api_key=comfy_api_key,
        )

    # ── Main build ──

    def build(self, shot_count, analysis_model, api_key, style_prompt,
              enable_subject_description, subject_description,
              # Shot 1
              shot_1_prompt, shot_1_camera_motion, shot_1_shot_type,
              shot_1_color_grading, shot_1_mood,
              shot_1_lighting_style,
              shot_1_use_image_color_grading,
              shot_1_use_image_mood, shot_1_use_image_lighting,
              # Shot 2
              shot_2_prompt, shot_2_camera_motion, shot_2_shot_type,
              shot_2_color_grading, shot_2_mood,
              shot_2_lighting_style,
              shot_2_use_image_color_grading,
              shot_2_use_image_mood, shot_2_use_image_lighting,
              # Shot 3
              shot_3_prompt, shot_3_camera_motion, shot_3_shot_type,
              shot_3_color_grading, shot_3_mood,
              shot_3_lighting_style,
              shot_3_use_image_color_grading,
              shot_3_use_image_mood, shot_3_use_image_lighting,
              **kwargs):

        # Extract ComfyUI API credentials (auto-injected hidden inputs)
        comfy_auth_token = kwargs.pop("auth_token_comfy_org", None)
        comfy_api_key = kwargs.pop("api_key_comfy_org", None)

        count = int(shot_count)

        # Pack per-shot data into a list for iteration
        shots_raw = [
            {
                "prompt": shot_1_prompt,
                "camera_motion": shot_1_camera_motion,
                "shot_type": shot_1_shot_type,
                "color_grading": shot_1_color_grading,
                "mood": shot_1_mood,
                "lighting_style": shot_1_lighting_style,
                "use_image_color_grading": shot_1_use_image_color_grading,
                "use_image_mood": shot_1_use_image_mood,
                "use_image_lighting": shot_1_use_image_lighting,
            },
            {
                "prompt": shot_2_prompt,
                "camera_motion": shot_2_camera_motion,
                "shot_type": shot_2_shot_type,
                "color_grading": shot_2_color_grading,
                "mood": shot_2_mood,
                "lighting_style": shot_2_lighting_style,
                "use_image_color_grading": shot_2_use_image_color_grading,
                "use_image_mood": shot_2_use_image_mood,
                "use_image_lighting": shot_2_use_image_lighting,
            },
            {
                "prompt": shot_3_prompt,
                "camera_motion": shot_3_camera_motion,
                "shot_type": shot_3_shot_type,
                "color_grading": shot_3_color_grading,
                "mood": shot_3_mood,
                "lighting_style": shot_3_lighting_style,
                "use_image_color_grading": shot_3_use_image_color_grading,
                "use_image_mood": shot_3_use_image_mood,
                "use_image_lighting": shot_3_use_image_lighting,
            },
        ]

        # ── Resolve image-driven parameters & build shot paragraphs ──
        shot_paragraphs = []
        for i in range(count):
            s = shots_raw[i]
            n = i + 1  # 1-based shot number

            color_grading = self._resolve_param(
                "color_grading", s["color_grading"],
                s["use_image_color_grading"], n, analysis_model, api_key, kwargs,
                comfy_auth_token=comfy_auth_token, comfy_api_key=comfy_api_key,
            )
            mood = self._resolve_param(
                "mood", s["mood"],
                s["use_image_mood"], n, analysis_model, api_key, kwargs,
                comfy_auth_token=comfy_auth_token, comfy_api_key=comfy_api_key,
            )
            lighting_style = self._resolve_param(
                "lighting_style", s["lighting_style"],
                s["use_image_lighting"], n, analysis_model, api_key, kwargs,
                comfy_auth_token=comfy_auth_token, comfy_api_key=comfy_api_key,
            )

            # Sora 2 best practice: repeat subject traits in every
            # shot so the model maintains character consistency.
            sub_desc = (
                subject_description.strip()
                if enable_subject_description and subject_description
                else ""
            )
            paragraph = self._format_shot_prose(
                prompt=s["prompt"],
                camera_motion=s["camera_motion"],
                shot_type=s["shot_type"],
                color_grading=color_grading,
                mood=mood,
                lighting_style=lighting_style,
                subject_description=sub_desc,
            )
            shot_paragraphs.append(paragraph)

        # ── Assemble the final Sora 2 video prompt ──
        prompt_parts = []

        # Style preamble (visual style spine shared across all shots)
        if style_prompt.strip():
            prompt_parts.append(style_prompt.strip())

        # Shot blocks — subject description is woven into each shot's
        # scene prose for cross-shot character consistency (Sora 2 best practice).
        if count == 1:
            prompt_parts.append(shot_paragraphs[0])
        else:
            for i, para in enumerate(shot_paragraphs):
                prompt_parts.append(f"Shot {i + 1}:\n{para}")

        video_prompt = "\n\n".join(prompt_parts)

        return (video_prompt,)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "ThreeShot": ThreeShot,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ThreeShot": "\U0001f3ac ThreeShot Sequence",
}
