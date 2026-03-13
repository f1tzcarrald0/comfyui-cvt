"""
ComfyUI Custom Node: Simple Gate
Passes input through if enabled, blocks it if disabled.
Works with any type (STRING, IMAGE, LATENT, MODEL, etc.)
"""


class SimpleGate:
    """Passes input through when enabled, blocks it when disabled."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("*",),
                "enabled": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "gate"
    CATEGORY = "SoraUtils"

    def gate(self, value, enabled):
        if enabled:
            return (value,)
        else:
            return (None,)


class SimpleGateString:
    """Passes string through when enabled, returns empty string when disabled."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {"forceInput": True}),
                "enabled": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "gate"
    CATEGORY = "SoraUtils"

    def gate(self, value, enabled):
        if enabled:
            return (value,)
        else:
            return ("",)


class SimpleGateImage:
    """Passes image through when enabled, blocks it when disabled."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("IMAGE",),
                "enabled": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "gate"
    CATEGORY = "SoraUtils"

    def gate(self, value, enabled):
        if enabled:
            return (value,)
        else:
            return (None,)


NODE_CLASS_MAPPINGS = {
    "SimpleGate": SimpleGate,
    "SimpleGateString": SimpleGateString,
    "SimpleGateImage": SimpleGateImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SimpleGate": "🚦 Gate (Any)",
    "SimpleGateString": "🚦 Gate (String)",
    "SimpleGateImage": "🚦 Gate (Image)",
}
