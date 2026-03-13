"""
ComfyUI Custom Node: Storyboard Prompt Assembler
Takes raw JSON output from the Gemini API partner node (containing 9 shot descriptions)
and assembles it into a Nano Banana Pro prompt for a 3×3 cinematic contact sheet.
"""

import json
import re


class StoryboardAssembler:
    """Parses 9 shots from Gemini JSON output and wraps them in a Nano Banana Pro grid prompt."""

    WRAPPER_TEMPLATE = """Analyze the input image. Identify every subject present — person(s), object(s), animal(s), vehicle(s). Lock their exact appearance: face, body type, proportions, hairstyle, hair color, skin tone, clothing, accessories, scars, tattoos, and all distinguishing features. These attributes are immutable across all nine panels.

Generate a single unified image: a "Cinematic 3x3 Contact Sheet" composed of nine panels arranged in a 3-column, 3-row grid. Each panel depicts one directed shot from a continuous scene. The panels are separated by thin black borders.

All nine panels share ONE continuous photographic reality:
- Same physical environment, same architecture, same props, same weather, same time of day
- Same color grading: unified white balance, color temperature, contrast curve, and tonal palette
- Same exposure level and lighting setup across all panels
- The subject(s) are unmistakably the same individual(s) from the input image in every panel, at every distance, from every angle

Each panel is rendered with high-end cinematic photo-realism: physically accurate lighting with correct shadow falloff, natural skin texture with subsurface scattering, realistic fabric weave and drape, optically correct depth of field matching the stated lens and f-stop, true perspective distortion for each focal length, natural motion blur where appropriate, no illustrated or painterly artifacts whatsoever.

THE NINE DIRECTED SHOTS (left-to-right, top-to-bottom):

Row 1 — Setup
Panel 1: {shot_1}
Panel 2: {shot_2}
Panel 3: {shot_3}

Row 2 — Core Action
Panel 4: {shot_4}
Panel 5: {shot_5}
Panel 6: {shot_6}

Row 3 — Resolution
Panel 7: {shot_7}
Panel 8: {shot_8}
Panel 9: {shot_9}

DEPTH OF FIELD RULES:
- Wide shots (14-35mm, f/5.6-f/11): deep focus, most of the environment sharp
- Medium shots (35-50mm, f/2.8-f/5.6): subject sharp, background softly defocused
- Close-ups (50-135mm, f/1.4-f/2.8): razor-thin focal plane on the subject, creamy bokeh background

LIKENESS ENFORCEMENT:
The subject(s) must be recognizable as the EXACT same individual(s) from the input image in every panel regardless of camera distance or angle. In wide shots, their silhouette, posture, and clothing must match. In close-ups, facial features, skin texture, and expression nuances must be faithful to the reference. There must be zero drift in identity, age, body type, hair, or wardrobe between panels.

The final image must look like a professional cinematographer's contact sheet: nine frames from a single continuous shoot, each with its own distinct composition and narrative beat, unified by absolute consistency in subject identity, environment, and photographic treatment."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gemini_output": ("STRING", {
                    "forceInput": True,
                    "tooltip": "Raw text output from the Gemini API partner node. Should contain a JSON array of 9 shot descriptions."
                }),
            },
            "optional": {
                "custom_wrapper": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Optional: replace the default Nano Banana wrapper. Must contain {shot_1} through {shot_9} placeholders."
                }),
                "prefix": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Optional text prepended before the assembled prompt."
                }),
                "suffix": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Optional text appended after the assembled prompt."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("assembled_prompt", "shot_list_preview",)
    FUNCTION = "assemble"
    CATEGORY = "SoraUtils"
    OUTPUT_NODE = False

    def _parse_shots(self, raw_text):
        """Extract exactly 9 shot strings from Gemini output. Handles multiple formats."""
        text = raw_text.strip()

        # Strip markdown code fences if present
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()

        # Strategy 1: Direct JSON array parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                if len(parsed) >= 9:
                    return [str(s) for s in parsed[:9]]
            # Handle {"shots": [...]} or any dict wrapping an array
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, list) and len(val) >= 9:
                        return [str(s) for s in val[:9]]
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find a JSON array anywhere in the text
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            try:
                shots = json.loads(match.group())
                if isinstance(shots, list) and len(shots) >= 9:
                    return [str(s) for s in shots[:9]]
            except json.JSONDecodeError:
                pass

        # Strategy 3: Numbered list fallback (1. "...", 2: ..., etc.)
        parts = re.split(r'\n\s*\d+[\.\):\-]\s*', text)
        parts = [p.strip().strip('"').strip("'").strip(',') for p in parts if len(p.strip()) > 20]
        if len(parts) >= 9:
            return parts[:9]

        # Strategy 4: Split by newlines and filter
        lines = [l.strip().strip('"').strip("'").strip(',') for l in text.split('\n') if len(l.strip()) > 30]
        if len(lines) >= 9:
            return lines[:9]

        raise ValueError(
            f"Could not parse 9 shots from Gemini output. "
            f"Expected a JSON array of 9 strings. Got:\n{raw_text[:500]}"
        )

    def assemble(self, gemini_output, custom_wrapper="", prefix="", suffix=""):
        shots = self._parse_shots(gemini_output)

        # Build preview
        preview_lines = [
            "── Row 1: Setup ──",
            f"  1: {shots[0]}",
            f"  2: {shots[1]}",
            f"  3: {shots[2]}",
            "",
            "── Row 2: Core Action ──",
            f"  4: {shots[3]}",
            f"  5: {shots[4]}",
            f"  6: {shots[5]}",
            "",
            "── Row 3: Resolution ──",
            f"  7: {shots[6]}",
            f"  8: {shots[7]}",
            f"  9: {shots[8]}",
        ]
        preview = "\n".join(preview_lines)

        # Assemble the prompt
        template = custom_wrapper.strip() if custom_wrapper.strip() else self.WRAPPER_TEMPLATE

        prompt = template.format(
            shot_1=shots[0], shot_2=shots[1], shot_3=shots[2],
            shot_4=shots[3], shot_5=shots[4], shot_6=shots[5],
            shot_7=shots[6], shot_8=shots[7], shot_9=shots[8],
        )

        if prefix.strip():
            prompt = prefix.strip() + "\n\n" + prompt
        if suffix.strip():
            prompt = prompt + "\n\n" + suffix.strip()

        return (prompt, preview,)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "StoryboardAssembler": StoryboardAssembler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StoryboardAssembler": "🎞️ Storyboard Assembler (Gemini → Nano Banana)",
}
