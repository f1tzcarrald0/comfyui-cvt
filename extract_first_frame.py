"""
ComfyUI Custom Node: Extract First Frame
Takes a VIDEO (from core Load Video node) and returns a single frame as IMAGE.
"""

import torch


class ExtractFirstFrame:
    """Extracts a frame from a VIDEO input (ComfyUI core Load Video node)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO", {
                    "tooltip": "Video input from the core Load Video node."
                }),
            },
            "optional": {
                "frame_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "tooltip": "Which frame to extract (0 = first frame)."
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("frame",)
    FUNCTION = "extract"
    CATEGORY = "CVT"

    def extract(self, video, frame_index=0):
        # video is a VideoInput object; get_components() returns VideoComponents
        # with .images as a (B, H, W, 3) torch tensor
        components = video.get_components()
        images = components.images

        # Clamp index to valid range
        idx = min(frame_index, images.shape[0] - 1)
        return (images[idx:idx+1],)


NODE_CLASS_MAPPINGS = {
    "ExtractFirstFrame": ExtractFirstFrame,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ExtractFirstFrame": "\U0001f39e\ufe0f Extract First Frame",
}
