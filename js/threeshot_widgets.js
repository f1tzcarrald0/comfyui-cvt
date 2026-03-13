/**
 * SoraUtils – ThreeShot dynamic widget management
 *
 * Handles showing/hiding widgets and image input sockets based on:
 *   - shot_count (1/2/3)            → hide inactive shot parameters
 *   - analysis_model                → show/hide api_key & image toggles
 *   - shot_N_use_image_*            → swap dropdown ↔ IMAGE socket
 */
import { app } from "../../scripts/app.js";

// ─────────────────────────────────────────────
//  Widget original state storage (WeakMap prevents property conflicts)
// ─────────────────────────────────────────────

const _originals = new WeakMap();

function _stash(widget) {
    if (!_originals.has(widget)) {
        _originals.set(widget, {
            type: widget.type,
            computeSize: widget.computeSize,
        });
    }
}

function _getOriginal(widget) {
    return _originals.get(widget);
}

// ─────────────────────────────────────────────
//  Widget visibility toggle
// ─────────────────────────────────────────────

function toggleWidget(node, widget, show) {
    if (!widget) return;

    _stash(widget);
    const orig = _getOriginal(widget);

    if (show) {
        widget.type = orig.type;
        widget.computeSize = orig.computeSize;
    } else {
        widget.type = "converted-widget";
        widget.computeSize = () => [0, -4];
    }
}

// ─────────────────────────────────────────────
//  Dynamic IMAGE input socket management
// ─────────────────────────────────────────────

function manageImageInput(node, inputName, show) {
    if (!node.inputs) node.inputs = [];

    const existingIndex = node.inputs.findIndex(
        (inp) => inp.name === inputName
    );

    if (show && existingIndex === -1) {
        node.addInput(inputName, "IMAGE");
    } else if (!show && existingIndex !== -1) {
        // Disconnect any link before removing
        const link = node.inputs[existingIndex].link;
        if (link != null && node.graph) {
            node.graph.removeLink(link);
        }
        node.removeInput(existingIndex);
    }
}

// ─────────────────────────────────────────────
//  Recalculate node size after visibility changes
// ─────────────────────────────────────────────

function refreshNodeSize(node) {
    // Force a fresh size computation
    const newSize = node.computeSize();
    // Keep current width (user may have resized), update height
    newSize[0] = Math.max(node.size[0], newSize[0]);
    node.setSize(newSize);
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas(true, true);
}

// ─────────────────────────────────────────────
//  The image-toggleable parameters and their widget names
// ─────────────────────────────────────────────

const IMAGE_PARAMS = ["color_grading", "mood", "lighting"];

function getParamInfo(n, param) {
    const toggleMap = {
        color_grading: `shot_${n}_use_image_color_grading`,
        mood: `shot_${n}_use_image_mood`,
        lighting: `shot_${n}_use_image_lighting`,
    };
    const dropdownMap = {
        color_grading: `shot_${n}_color_grading`,
        mood: `shot_${n}_mood`,
        lighting: `shot_${n}_lighting_style`,
    };
    return {
        toggleName: toggleMap[param],
        dropdownName: dropdownMap[param],
        imageName: `shot_${n}_image_${param}`,
    };
}

// ─────────────────────────────────────────────
//  Extension registration
// ─────────────────────────────────────────────

app.registerExtension({
    name: "SoraUtils.ThreeShot",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (nodeData.name !== "ThreeShot") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated
                ? onNodeCreated.apply(this, arguments)
                : undefined;

            const node = this;
            setupThreeShot(node);
            return ret;
        };

        // Handle workflow load / paste
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) {
                onConfigure.apply(this, arguments);
            }
            const node = this;
            // Delay to let widgets deserialize values first
            setTimeout(() => {
                recreateDynamicInputs(node);
                updateAllVisibility(node);
            }, 200);
        };
    },
});

// ─────────────────────────────────────────────
//  Setup: attach callbacks and run initial pass
// ─────────────────────────────────────────────

function setupThreeShot(node) {
    // Helper: find widget by name
    const findWidget = (name) =>
        node.widgets ? node.widgets.find((wg) => wg.name === name) : null;

    // List of widget names that control visibility of other widgets
    const controlNames = ["shot_count", "analysis_model", "enable_subject_description"];
    for (let n = 1; n <= 3; n++) {
        controlNames.push(
            `shot_${n}_use_image_color_grading`,
            `shot_${n}_use_image_mood`,
            `shot_${n}_use_image_lighting`
        );
    }

    // Attach a callback to each controlling widget
    for (const name of controlNames) {
        const widget = findWidget(name);
        if (!widget) continue;

        const origCallback = widget.callback;
        widget.callback = function (...args) {
            if (origCallback) {
                origCallback.apply(this, args);
            }
            updateAllVisibility(node);
        };
    }

    // Initial visibility pass (delayed so widgets are fully ready)
    setTimeout(() => updateAllVisibility(node), 150);
}

// ─────────────────────────────────────────────
//  Recreate dynamic image inputs on workflow load
// ─────────────────────────────────────────────

function recreateDynamicInputs(node) {
    const findWidget = (name) =>
        node.widgets ? node.widgets.find((wg) => wg.name === name) : null;

    const count = parseInt(findWidget("shot_count")?.value || "3", 10);
    const model = findWidget("analysis_model")?.value || "none";
    const canUseImages = model !== "none";

    for (let n = 1; n <= 3; n++) {
        for (const param of IMAGE_PARAMS) {
            const info = getParamInfo(n, param);
            const useImage =
                n <= count &&
                canUseImages &&
                findWidget(info.toggleName)?.value === true;
            const exists = node.inputs
                ? node.inputs.some((inp) => inp.name === info.imageName)
                : false;

            if (useImage && !exists) {
                node.addInput(info.imageName, "IMAGE");
            }
        }
    }
}

// ─────────────────────────────────────────────
//  Master visibility update
// ─────────────────────────────────────────────

function updateAllVisibility(node) {
    const findWidget = (name) =>
        node.widgets ? node.widgets.find((wg) => wg.name === name) : null;

    const count = parseInt(findWidget("shot_count")?.value || "3", 10);
    const model = findWidget("analysis_model")?.value || "none";
    const needsApiKey = ["Gemini", "ChatGPT", "Claude"].includes(model);
    const canUseImages = model !== "none";

    // ── api_key: show only when an API-based model is selected ──
    toggleWidget(node, findWidget("api_key"), needsApiKey);

    // ── subject_description: show only when toggle is on ──
    const subjectEnabled = !!findWidget("enable_subject_description")?.value;
    toggleWidget(node, findWidget("subject_description"), subjectEnabled);

    // ── Per-shot visibility ──
    for (let n = 1; n <= 3; n++) {
        const active = n <= count;

        // Names of ALL widgets belonging to this shot
        const allShotWidgets = [
            `shot_${n}_prompt`,
            `shot_${n}_camera_motion`,
            `shot_${n}_shot_type`,
            `shot_${n}_color_grading`,
            `shot_${n}_mood`,
            `shot_${n}_lighting_style`,
            `shot_${n}_use_image_color_grading`,
            `shot_${n}_use_image_mood`,
            `shot_${n}_use_image_lighting`,
        ];

        // ── INACTIVE shot: hide everything, remove all image inputs ──
        if (!active) {
            for (const wname of allShotWidgets) {
                toggleWidget(node, findWidget(wname), false);
            }
            for (const param of IMAGE_PARAMS) {
                const info = getParamInfo(n, param);
                manageImageInput(node, info.imageName, false);
            }
            continue;
        }

        // ── ACTIVE shot ──

        // Always-visible core widgets
        toggleWidget(node, findWidget(`shot_${n}_prompt`), true);
        toggleWidget(node, findWidget(`shot_${n}_camera_motion`), true);
        toggleWidget(node, findWidget(`shot_${n}_shot_type`), true);

        // Image-toggleable parameters
        for (const param of IMAGE_PARAMS) {
            const info = getParamInfo(n, param);
            const toggleWgt = findWidget(info.toggleName);
            const dropdownWgt = findWidget(info.dropdownName);
            const useImage = canUseImages && toggleWgt?.value === true;

            // Show/hide the use_image toggle (only visible when a model is selected)
            toggleWidget(node, toggleWgt, canUseImages);

            // Show dropdown when NOT using image; hide when using image
            toggleWidget(node, dropdownWgt, !useImage);

            // Add/remove the IMAGE input socket
            manageImageInput(node, info.imageName, useImage);
        }
    }

    // ── Refresh node layout ──
    refreshNodeSize(node);
}
