# CVT - Cinematic Video Tools

Cinematic video prompt tools for ComfyUI.

## Nodes

### ThreeShot Sequence
Builds 1-3 shot video prompts with per-shot controls for camera motion, framing, color grading, mood, and lighting. Supports image-driven parameter extraction via CLIP, Qwen 3 VL, Gemini, ChatGPT, Claude, or the ComfyUI API proxy.

### SceneCamera
Takes a scene image and a camera movement selection, outputs an optimized video prompt with 25 camera move presets (push in, orbit, crane, dolly zoom, drone, steadicam, etc.).

### Storyboard Assembler
Parses 9 shot descriptions from Gemini API output and assembles them into a prompt for a 3x3 cinematic contact sheet.

### Extract First Frame
Extracts a single frame from a VIDEO input as an IMAGE.

### Gate Nodes
Simple pass-through gates (Any, String, Image) that enable/disable signal flow with a boolean toggle.

### Image Concatenate Multi
Concatenates multiple images in any direction with optional size matching.

### List To Batch
Converts a list of images into a batched IMAGE tensor.

## Installation

Install via the [Comfy Registry](https://registry.comfy.org):

```
comfy node install comfyui-cvt
```

Or clone into your `custom_nodes` directory:

```
cd ComfyUI/custom_nodes
git clone https://github.com/f1tzcarrald0/comfyui-cvt.git
pip install -r comfyui-cvt/requirements.txt
```

## Example Workflows

See the `example_workflows/` folder for ready-to-use workflow files.

## Vision Analysis Models

The ThreeShot node can analyze input images to automatically determine color grading, mood, and lighting parameters. Supported backends:

| Model | Type | Requirements |
|-------|------|-------------|
| CLIP | Local | `transformers` (included in dependencies) |
| Qwen 3 VL 8B | Local | GPU with 16GB+ VRAM, auto-downloads model |
| Gemini | API | Google AI API key |
| ChatGPT | API | OpenAI API key |
| Claude | API | Anthropic API key |
| ChatGPT (ComfyUI) | API proxy | ComfyUI account (uses account credits) |
