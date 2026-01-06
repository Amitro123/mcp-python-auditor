"""
Fix kaggle_finetune.ipynb to resolve PyTorch version conflicts.

This script updates the installation cell to pin compatible PyTorch versions
before installing Unsloth.
"""

import json

# Read the notebook
notebook_path = 'finetune/kaggle_finetune.ipynb'
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Updated installation cell source
new_install_source = [
    "import sys\\n",
    "\\n",
    "# Step 1: Install compatible PyTorch versions FIRST\\n",
    "print(\"⏳ Step 1/3: Installing PyTorch 2.8.0 + torchvision 0.23.0...\")\\n",
    "!pip install -q torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126 2>&1 | tail -5\\n",
    "\\n",
    "# Step 2: Install Unsloth (will use existing PyTorch)\\n",
    "print(\"\\n⏳ Step 2/3: Installing Unsloth (this takes 3-4 minutes)...\")\\n",
    "!pip install -q \"unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git\" 2>&1 | grep -v \"Requirement already satisfied\" | tail -20\\n",
    "\\n",
    "# Step 3: Install xformers\\n",
    "print(\"\\n⏳ Step 3/3: Installing xformers...\")\\n",
    "!pip install -q xformers --upgrade 2>&1 | grep -v \"Requirement already satisfied\" | tail -10\\n",
    "\\n",
    "print(\"\\n✅ Installation complete!\\n\")\\n",
    "\\n",
    "# Verify versions\\n",
    "import torch\\n",
    "import torchvision\\n",
    "print(f\"✅ torch: {torch.__version__}\")\\n",
    "print(f\"✅ torchvision: {torchvision.__version__}\")"
]

# Find and update the installation cell (cell index 2, which is the first code cell)
for i, cell in enumerate(notebook['cells']):
    if cell['cell_type'] == 'code' and i == 2:  # First code cell
        cell['source'] = new_install_source
        print(f"[OK] Updated cell {i} (Installation cell)")
        break

# Save the updated notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("[OK] Notebook updated successfully!")
print("\n[CHANGES]:")
print("  - Pinned torch==2.8.0, torchvision==0.23.0, torchaudio==2.8.0")
print("  - Added version verification at the end")
print("  - Split installation into 3 clear steps")
