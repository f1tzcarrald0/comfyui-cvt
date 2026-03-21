"""
ComfyUI Custom Node: ThreeShotSimple
Simplified 3-shot sequence builder with only camera motion and shot type
per shot. Outputs system_prompt, user_prompt, and preview for LLM-driven
prompt generation via the OpenAI ChatGPT node.
"""

from .presets import CAMERA_MOTIONS, CAMERA_SHOT_TYPES

DEFAULT_SYSTEM_PROMPT = (
    "You are a cinematic video prompt writer for Sora 2. "
    "Given a 3-shot sequence with camera motion and framing for each shot, "
    "write a single cohesive, vivid video prompt optimized for Sora 2 video "
    "generation. Keep each shot to 80\u2013150 words of rich prose. "
    "Front-load the most important visual details in each shot. "
    "Output only the final prompt with Shot 1, Shot 2, Shot 3 sections."
)


class ThreeShotSimple:
    """Simplified 3-shot sequence \u2014 camera motion & shot type only."""

    @classmethod
    def INPUT_TYPES(cls):
        required = {}

        required["style_prompt"] = ("STRING", {
            "multiline": True,
            "default": "",
            "tooltip": "Overall visual style, mood, genre, or aesthetic that applies to all shots.",
        })

        for n in range(1, 4):
            required[f"shot_{n}_prompt"] = ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": f"What happens in shot {n} \u2014 subject, action, emotion, key details.",
            })
            required[f"shot_{n}_camera_motion"] = (CAMERA_MOTIONS, {
                "tooltip": f"Shot {n}: Camera movement.",
            })
            required[f"shot_{n}_shot_type"] = (CAMERA_SHOT_TYPES, {
                "tooltip": f"Shot {n}: Framing / camera angle.",
            })

        required["subject_description"] = ("STRING", {
            "multiline": True,
            "default": "",
            "tooltip": "Subject appearance description to maintain consistency across shots.",
        })

        return {"required": required}

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("system_prompt", "user_prompt", "preview")
    FUNCTION = "build"
    CATEGORY = "SoraUtils"
    OUTPUT_NODE = False

    def build(self, style_prompt,
              shot_1_prompt, shot_1_camera_motion, shot_1_shot_type,
              shot_2_prompt, shot_2_camera_motion, shot_2_shot_type,
              shot_3_prompt, shot_3_camera_motion, shot_3_shot_type,
              subject_description):

        # ── System prompt (instructions for the LLM) ──
        system_prompt = DEFAULT_SYSTEM_PROMPT

        # ── User prompt (assembled shot details) ──
        parts = []

        if style_prompt.strip():
            parts.append(f"Overall style: {style_prompt.strip()}")

        if subject_description.strip():
            parts.append(
                f"Subject (consistent across all shots): "
                f"{subject_description.strip()}"
            )

        shots = [
            (shot_1_prompt, shot_1_camera_motion, shot_1_shot_type),
            (shot_2_prompt, shot_2_camera_motion, shot_2_shot_type),
            (shot_3_prompt, shot_3_camera_motion, shot_3_shot_type),
        ]

        for i, (prompt, cam, shot) in enumerate(shots, 1):
            shot_lines = [f"Shot {i}:"]
            if prompt.strip():
                shot_lines.append(f"  Description: {prompt.strip()}")
            shot_lines.append(f"  Camera motion: {cam}")
            shot_lines.append(f"  Shot type: {shot}")
            parts.append("\n".join(shot_lines))

        user_prompt = "\n\n".join(parts)

        # ── Preview (combined view for debugging) ──
        preview = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== USER PROMPT ===\n{user_prompt}"

        return (system_prompt, user_prompt, preview)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "ThreeShotSimple": ThreeShotSimple,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ThreeShotSimple": "\U0001f3ac ThreeShot Sequence",
}
