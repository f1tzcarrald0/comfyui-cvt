"""
ComfyUI Custom Node: Image Concatenate Multi
Copied from ComfyUI-KJNodes (kijai), adapted for this nodepack registration.
"""

import torch
from comfy.utils import common_upscale


class ImageConcanate:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "direction": (
                    [
                        "right",
                        "down",
                        "left",
                        "up",
                    ],
                    {"default": "right"},
                ),
                "match_image_size": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "concatenate"
    CATEGORY = "SoraUtils"
    DESCRIPTION = """
    Concatenates the image2 to image1 in the specified direction.
    """

    def concatenate(self, image1, image2, direction, match_image_size, first_image_shape=None):
        batch_size1 = image1.shape[0]
        batch_size2 = image2.shape[0]
        if batch_size1 != batch_size2:
            max_batch_size = max(batch_size1, batch_size2)
            repeats1 = max_batch_size - batch_size1
            repeats2 = max_batch_size - batch_size2
            if repeats1 > 0:
                last_image1 = image1[-1].unsqueeze(0).repeat(repeats1, 1, 1, 1)
                image1 = torch.cat([image1.clone(), last_image1], dim=0)
            if repeats2 > 0:
                last_image2 = image2[-1].unsqueeze(0).repeat(repeats2, 1, 1, 1)
                image2 = torch.cat([image2.clone(), last_image2], dim=0)

        if match_image_size:
            target_shape = first_image_shape if first_image_shape is not None else image1.shape
            original_height = image2.shape[1]
            original_width = image2.shape[2]
            original_aspect_ratio = original_width / original_height

            if direction in ["left", "right"]:
                target_height = target_shape[1]
                target_width = int(target_height * original_aspect_ratio)
            elif direction in ["up", "down"]:
                target_width = target_shape[2]
                target_height = int(target_width / original_aspect_ratio)

            image2_for_upscale = image2.movedim(-1, 1)
            image2_resized = common_upscale(
                image2_for_upscale, target_width, target_height, "lanczos", "disabled"
            )
            image2_resized = image2_resized.movedim(1, -1)
        else:
            image2_resized = image2

        channels_image1 = image1.shape[-1]
        channels_image2 = image2_resized.shape[-1]
        if channels_image1 != channels_image2:
            if channels_image1 < channels_image2:
                alpha_channel = torch.ones(
                    (*image1.shape[:-1], channels_image2 - channels_image1), device=image1.device
                )
                image1 = torch.cat((image1, alpha_channel), dim=-1)
            else:
                alpha_channel = torch.ones(
                    (*image2_resized.shape[:-1], channels_image1 - channels_image2),
                    device=image2_resized.device,
                )
                image2_resized = torch.cat((image2_resized, alpha_channel), dim=-1)

        if direction == "right":
            concatenated_image = torch.cat((image1, image2_resized), dim=2)
        elif direction == "down":
            concatenated_image = torch.cat((image1, image2_resized), dim=1)
        elif direction == "left":
            concatenated_image = torch.cat((image2_resized, image1), dim=2)
        elif direction == "up":
            concatenated_image = torch.cat((image2_resized, image1), dim=1)

        return concatenated_image,


class ImageConcatMulti:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "inputcount": ("INT", {"default": 2, "min": 2, "max": 1000, "step": 1}),
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "direction": (
                    [
                        "right",
                        "down",
                        "left",
                        "up",
                    ],
                    {"default": "right"},
                ),
                "match_image_size": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "combine"
    CATEGORY = "SoraUtils"
    DESCRIPTION = """
    Creates an image from multiple images.
    You can set how many inputs the node has, with the **inputcount** and clicking update.
    """

    def combine(self, inputcount, direction, match_image_size, **kwargs):
        image = kwargs["image_1"]
        first_image_shape = None
        if first_image_shape is None:
            first_image_shape = image.shape
        for c in range(1, inputcount):
            new_image = kwargs[f"image_{c + 1}"]
            image, = ImageConcanate.concatenate(
                self,
                image,
                new_image,
                direction,
                match_image_size,
                first_image_shape=first_image_shape,
            )
        first_image_shape = None
        return (image,)


NODE_CLASS_MAPPINGS = {
    "ImageConcatMulti": ImageConcatMulti,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageConcatMulti": "Image Concatenate Multi",
}
