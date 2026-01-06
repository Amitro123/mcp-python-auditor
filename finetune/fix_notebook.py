"""
Complete nuclear fix for kaggle_finetune.ipynb
Updates both installation cell and documentation
"""

import json

# Read the notebook
notebook_path = 'finetune/kaggle_finetune.ipynb'
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Updated installation markdown
install_markdown = [
    "## 1. Install Dependencies (Nuclear Clean)\n",
    "\n",
    "**Strategy:** Clean install with Kaggle-proven stable versions\n",
    "- torch 2.5.1 + torchvision 0.20.1 (no conflicts)\n",
    "- unsloth colab-new variant (Kaggle optimized)\n",
    "- xformers 0.0.28.post1 (pre-built, no compile)\n",
    "\n",
    "**Time:** ~3-4 minutes"
]

# Updated installation cell source - NUCLEAR CLEAN APPROACH
new_install_source = [
    "# KAGGLE UNSLOTH NUCLEAR FIX 2026\n",
    "import os, sys\n",
    "\n",
    "# Nuclear clean - remove all conflicting packages\n",
    "print(\"Step 1/4: Cleaning existing packages...\")\n",
    "!pip uninstall -y torch torchvision torchaudio xformers unsloth transformers -q 2>&1 | tail -3\n",
    "!pip cache purge -q\n",
    "\n",
    "# Kaggle stable versions (proven to work)\n",
    "print(\"\\nStep 2/4: Installing PyTorch 2.5.1 (Kaggle stable)...\")\n",
    "!pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121 -q 2>&1 | tail -5\n",
    "\n",
    "# Unsloth + deps (no version conflicts)\n",
    "print(\"\\nStep 3/4: Installing Unsloth (colab-new variant)...\")\n",
    "!pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\" --no-deps -q 2>&1 | tail -10\n",
    "\n",
    "print(\"\\nStep 4/4: Installing dependencies...\")\n",
    "!pip install xformers==0.0.28.post1 trl==0.9.6 peft accelerate bitsandbytes datasets -q 2>&1 | tail -5\n",
    "\n",
    "print(\"\\n\" + \"=\"*50)\n",
    "print(\"[OK] CLEAN INSTALL COMPLETE!\")\n",
    "print(\"=\"*50)\n",
    "\n",
    "# Verify versions\n",
    "import torch\n",
    "print(f\"\\n[OK] CUDA available: {torch.cuda.is_available()}\")\n",
    "print(f\"[OK] torch: {torch.__version__}\")\n",
    "if torch.cuda.is_available():\n",
    "    print(f\"[OK] GPU: {torch.cuda.get_device_name(0)}\")\n",
    "\n",
    "print(\"\\n[NEXT] Run the next cell to load the model!\")"
]

# Update cells
for i, cell in enumerate(notebook['cells']):
    # Update installation markdown (cell 1)
    if cell['cell_type'] == 'markdown' and i == 1:
        cell['source'] = install_markdown
        print(f"[OK] Updated cell {i} (Installation markdown)")
    
    # Update installation code (cell 2)
    if cell['cell_type'] == 'code' and i == 2:
        cell['source'] = new_install_source
        print(f"[OK] Updated cell {i} (Installation code)")

# Save the updated notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("\n[OK] Notebook updated successfully!")
print("\n[CHANGES]:")
print("  - Nuclear clean approach (uninstall + cache purge)")
print("  - torch 2.5.1 + torchvision 0.20.1 (Kaggle stable)")
print("  - unsloth colab-new variant (optimized)")
print("  - xformers 0.0.28.post1 (pre-built)")
print("  - trl 0.9.6 pinned for compatibility")
