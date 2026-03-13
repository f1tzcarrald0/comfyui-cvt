"""
ComfyUI Custom Node: List To Batch
Copied from ComfyUI_essentials ImageListToBatch behavior.
"""

import torch
import comfy.utils


class ListToBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    INPUT_IS_LIST = True
    CATEGORY = "SoraUtils"

    def execute(self, image):
        shape = image[0].shape[1:3]
        out = []
        for i in range(len(image)):
            img = image[i]
            if image[i].shape[1:3] != shape:
                img = comfy.utils.common_upscale(
                    img.permute([0, 3, 1, 2]),
                    shape[1],
                    shape[0],
                    upscale_method="bicubic",
                    crop="center",
                ).permute([0, 2, 3, 1])
            out.append(img)
        out = torch.cat(out, dim=0)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "ListToBatch": ListToBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ListToBatch": "List To Batch",
}
