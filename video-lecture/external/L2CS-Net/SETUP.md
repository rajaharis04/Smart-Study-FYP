# L2CS-Net — Vendored Gaze Estimation (OPTIONAL)

This directory is a placeholder for the **L2CS-Net** gaze-estimation model,
which the Attention & Presence Monitor uses **optionally** (feature-flagged via
`ATTN_ENABLE_GAZE`, default **off**). The core attention pipeline
(MediaPipe Face Mesh + EAR + head-pose + DeepFace recognition) works fully
**without** this — gaze only *adds* a "looking at screen" confirmation.

## Attribution & License

- **Project:** L2CS-Net — *"L2CS-Net: Fine-Grained Gaze Estimation in
  Unconstrained Environments"* (Abdelrahman et al.)
- **Source:** https://github.com/Ahmednull/L2CS-Net
- **License:** MIT

When you clone the repository into this folder, **keep its original `LICENSE`
file in place**. The wrapper that imports it
(`video-lecture/modules/attention_monitor/gaze.py`) carries an attribution
comment pointing back here, satisfying the module's licensing requirement.

## Installation (only if you want gaze)

From the repository root, inside the dedicated CV virtualenv:

```bash
# 1) Clone L2CS-Net into this exact folder
git clone https://github.com/Ahmednull/L2CS-Net video-lecture/external/L2CS-Net

# 2) Install PyTorch (choose the CPU or CUDA build for your machine)
pip install torch torchvision

# 3) Install L2CS-Net as an editable package (provides the `l2cs` import)
pip install -e video-lecture/external/L2CS-Net

# 4) Download the pretrained Gaze360 weights per the L2CS-Net README
#    (e.g. L2CSNet_gaze360.pkl) and place them under:
#        video-lecture/external/L2CS-Net/models/L2CSNet_gaze360.pkl

# 5) Enable the feature via environment variables
#    Windows (PowerShell):
#        $env:ATTN_ENABLE_GAZE = "true"
#        $env:ATTN_GAZE_WEIGHTS_PATH = "video-lecture/external/L2CS-Net/models/L2CSNet_gaze360.pkl"
#    Linux/macOS:
#        export ATTN_ENABLE_GAZE=true
#        export ATTN_GAZE_WEIGHTS_PATH=video-lecture/external/L2CS-Net/models/L2CSNet_gaze360.pkl
```

## Verify

Hit the diagnostic endpoint (backend running from the CV venv):

```
GET /api/attention/status
```

You should see `"gaze_enabled": true` and `"gaze_available": true`. If
`gaze_available` is `false`, the `gaze_load_error` field explains why
(missing weights, Torch not installed, etc.) — and the pipeline will simply
continue **without** gaze, never blocking attention.

> Note: This folder is intentionally kept out of version control except for
> this `SETUP.md` (see `.gitignore`). Do not commit large model weights.
