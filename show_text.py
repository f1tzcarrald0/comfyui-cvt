"""
ComfyUI Custom Node: ShowText
Simple debug node that displays any text value on the canvas.
Replaces 'easy showAnything' dependency.
"""


class ShowText:
    """Display any text/string value on the canvas for debugging."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "anything": ("*",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "show"
    CATEGORY = "SoraUtils"
    OUTPUT_NODE = True
    INPUT_IS_LIST = False

    def show(self, anything=None):
        text = str(anything) if anything is not None else ""
        return {"ui": {"text": [text]}, "result": (text,)}


NODE_CLASS_MAPPINGS = {
    "ShowText": ShowText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ShowText": "📝 Show Text",
}
