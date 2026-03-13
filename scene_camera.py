"""
ComfyUI Custom Node: SceneCamera
Takes a scene image and a camera movement selection, then generates
a Sora 2 optimized video prompt using a preset prompt template for
the chosen camera move. No vision analysis required.

Outputs a single Sora-ready video prompt.
"""

CAMERA_MOVES = {
    "slow push in": (
        "The camera slowly pushes in toward the subject, gradually tightening "
        "the frame. Smooth, steady forward motion that draws the viewer deeper "
        "into the scene. The background subtly compresses as the camera advances."
    ),
    "slow pull out": (
        "The camera slowly pulls back, widening the frame to reveal more of the "
        "surrounding environment. Steady, continuous backward motion that unveils "
        "spatial context and scale around the subject."
    ),
    "arc left around subject": (
        "The camera arcs smoothly to the left around the subject in a semicircular "
        "path, maintaining consistent distance and focus. The background shifts and "
        "parallax reveals new depth as perspective rotates."
    ),
    "arc right around subject": (
        "The camera arcs smoothly to the right around the subject in a semicircular "
        "path, maintaining consistent distance and focus. The background shifts and "
        "parallax reveals new depth as perspective rotates."
    ),
    "handheld drift": (
        "Subtle handheld camera movement with organic, breathing drift. Slight "
        "imperfections in the motion lend a naturalistic, documentary feel. The "
        "frame gently sways with lifelike instability."
    ),
    "360 orbit around subject": (
        "The camera orbits a full 360 degrees around the subject in a smooth, "
        "continuous circular path. The environment rotates behind the subject, "
        "revealing every angle of the scene with consistent speed and distance."
    ),
    "crane up (rising reveal)": (
        "The camera rises vertically in a smooth crane movement, lifting above "
        "the subject to reveal the broader landscape below. A dramatic ascending "
        "reveal that transitions from intimate detail to expansive overview."
    ),
    "crane down (descending into scene)": (
        "The camera descends smoothly from an elevated position down into the "
        "scene. A crane movement that brings the viewer from an overview into "
        "intimate proximity with the subject and environment."
    ),
    "dolly zoom (vertigo effect)": (
        "The camera dollies forward while simultaneously zooming out, or dollies "
        "back while zooming in, creating a disorienting vertigo effect. The subject "
        "stays the same size while the background dramatically warps in perspective."
    ),
    "steady tracking forward": (
        "The camera tracks steadily forward through the scene on a straight path. "
        "Smooth, continuous forward motion at a consistent speed. The environment "
        "opens up ahead as the camera advances deeper into the space."
    ),
    "steady tracking alongside": (
        "The camera tracks laterally alongside the subject, moving in parallel "
        "at a matching pace. Smooth side-to-side motion that maintains framing "
        "while the background scrolls past in parallax."
    ),
    "whip pan left": (
        "The camera rapidly whip-pans to the left with motion blur streaking "
        "across the frame. A fast, energetic horizontal sweep that creates a "
        "jarring transition and sense of urgent momentum."
    ),
    "whip pan right": (
        "The camera rapidly whip-pans to the right with motion blur streaking "
        "across the frame. A fast, energetic horizontal sweep that creates a "
        "jarring transition and sense of urgent momentum."
    ),
    "drone flyover": (
        "An aerial drone shot gliding smoothly over the scene from above. The "
        "camera looks down at an angle, revealing the geography and layout of "
        "the environment as it passes overhead at a steady altitude."
    ),
    "drone fly-through": (
        "An aerial drone shot flying forward through the scene at mid-level "
        "height, weaving between elements of the environment. Dynamic forward "
        "motion that immerses the viewer in the space from a bird's perspective."
    ),
    "first-person POV walk-through": (
        "A first-person point-of-view shot walking through the scene at eye "
        "level. Slight natural bobbing with each step. The environment unfolds "
        "ahead as if the viewer is physically present and moving through the space."
    ),
    "slow orbit clockwise": (
        "The camera slowly orbits clockwise around the subject, maintaining "
        "steady distance and focus. A gentle, meditative rotation that gradually "
        "reveals different angles of the scene and subject."
    ),
    "slow orbit counterclockwise": (
        "The camera slowly orbits counterclockwise around the subject, maintaining "
        "steady distance and focus. A gentle, meditative rotation that gradually "
        "reveals different angles of the scene and subject."
    ),
    "dolly forward through scene": (
        "The camera dollies forward on a straight path through the scene, passing "
        "between objects and through layers of the environment. Smooth, deliberate "
        "forward motion that creates depth and immersion."
    ),
    "cable cam glide": (
        "The camera glides along an invisible cable path above the scene, moving "
        "smoothly in a straight or gently curved line. Stable, elevated perspective "
        "with fluid motion and no vibration."
    ),
    "steadicam follow": (
        "The camera follows behind or alongside the subject using smooth steadicam "
        "stabilization. Fluid, floating motion that tracks the subject's movement "
        "through the scene while absorbing any irregularities in the path."
    ),
    "jib arm sweep": (
        "The camera sweeps in a wide arc on a jib arm, combining horizontal and "
        "vertical movement. A dramatic, sweeping motion that covers a large area "
        "of the scene with elegant, curved trajectory."
    ),
    "tilt up reveal": (
        "The camera tilts upward from a low starting position, gradually revealing "
        "the scene from bottom to top. A vertical pan that builds anticipation "
        "and unveils the full scale of the environment or subject."
    ),
    "tilt down reveal": (
        "The camera tilts downward from a high starting position, gradually "
        "revealing the scene from top to bottom. A vertical pan that descends "
        "from sky or ceiling to reveal the ground-level subject and detail."
    ),
    "zoom in (lens zoom)": (
        "The camera zooms in using the lens, tightening the focal length to "
        "magnify the subject without physical camera movement. The background "
        "flattens and compresses as the field of view narrows."
    ),
    "zoom out (lens zoom)": (
        "The camera zooms out using the lens, widening the focal length to "
        "reveal more of the scene without physical camera movement. The "
        "perspective expands and depth increases as the field of view widens."
    ),
}

CAMERA_MOVE_NAMES = list(CAMERA_MOVES.keys())


class SceneCamera:
    """Takes a scene image and generates a Sora 2 camera-movement video prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "Scene image to build a camera-move prompt for.",
                }),
                "camera_move": (CAMERA_MOVE_NAMES, {
                    "tooltip": "Camera movement to apply through/around the scene.",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_prompt",)
    FUNCTION = "build"
    CATEGORY = "SoraUtils"
    OUTPUT_NODE = False

    def build(self, image, camera_move):
        # Get the preset prompt for the selected camera movement
        camera_prompt = CAMERA_MOVES[camera_move]

        video_prompt = camera_prompt.strip()
        return (video_prompt,)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "SceneCamera": SceneCamera,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SceneCamera": "\U0001f3a5 SceneCamera",
}
