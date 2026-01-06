"""
Production Kaggle Notebook Generator - NUMPY BINARY FIX
Key: Use numpy 2.x compatible with torch 2.5.1, OR force reinstall
"""

import json

notebook_path = 'finetune/kaggle_finetune.ipynb'
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# ============================================================================
# CELL 0: Title
# ============================================================================
cell_0_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# Fine-tune Gemma-2-2b for Code Audit (Kaggle T4)\n",
        "\n",
        "**Production Notebook** | Amit Rosen | Ashkelon, Israel | 2026\n",
        "\n",
        "| Setting | Value |\n",
        "|---------|-------|\n",
        "| Model | `unsloth/gemma-2-2b-it-bnb-4bit` |\n",
        "| GPU | Tesla T4 (16GB VRAM) |\n",
        "| Train Time | ~25 min |"
    ]
}

# ============================================================================
# CELL 1: Install - NUMPY 2.x FIX
# ============================================================================
cell_1_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 1. Install Dependencies\n",
        "\n",
        "**Run this cell, then RESTART KERNEL before continuing!**"
    ]
}

# The key insight: torch 2.5.1 needs numpy 2.x, not 1.26.4
cell_1_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# KAGGLE UNSLOTH INSTALL - NUMPY 2.x COMPATIBLE\n",
        "# Run this cell, then RESTART KERNEL!\n",
        "\n",
        "import subprocess\n",
        "import sys\n",
        "import os\n",
        "\n",
        "def run(cmd, msg):\n",
        "    print(msg)\n",
        "    subprocess.run(cmd, shell=True, capture_output=True)\n",
        "\n",
        "# Step 1: Upgrade PyTorch to 2.5.1\n",
        "run(\n",
        "    \"pip install -q torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121\",\n",
        "    \"[1/5] Installing PyTorch 2.5.1...\"\n",
        ")\n",
        "\n",
        "# Step 2: Force reinstall numpy (binary compatible with new torch)\n",
        "run(\n",
        "    \"pip install -q --force-reinstall numpy\",\n",
        "    \"[2/5] Reinstalling numpy (binary fix)...\"\n",
        ")\n",
        "\n",
        "# Step 3: Install Unsloth with specific unsloth_zoo\n",
        "run(\n",
        "    'pip install -q \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"',\n",
        "    \"[3/5] Installing Unsloth...\"\n",
        ")\n",
        "run(\"pip install -q unsloth_zoo\", \"     + unsloth_zoo...\")\n",
        "\n",
        "# Step 4: Training dependencies\n",
        "run(\n",
        "    \"pip install -q trl==0.9.6 peft accelerate bitsandbytes datasets\",\n",
        "    \"[4/5] Installing training dependencies...\"\n",
        ")\n",
        "\n",
        "# Step 5: xformers\n",
        "run(\"pip install -q xformers==0.0.28.post3\", \"[5/5] Installing xformers...\")\n",
        "\n",
        "print(\"\\n\" + \"=\"*60)\n",
        "print(\"[OK] Installation complete!\")\n",
        "print(\"=\"*60)\n",
        "print(\"\\n\" + \"*\"*60)\n",
        "print(\"*** IMPORTANT: RESTART KERNEL NOW! ***\")\n",
        "print(\"*** Then run Cell 2 (skip this cell) ***\")\n",
        "print(\"*\"*60)"
    ]
}

# ============================================================================
# CELL 2: Verify Install (run AFTER kernel restart)
# ============================================================================
cell_2_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 2. Verify Installation\n",
        "\n",
        "Run this AFTER kernel restart"
    ]
}

cell_2_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Verify installation (run after kernel restart)\n",
        "import torch\n",
        "import numpy as np\n",
        "\n",
        "print(f\"[OK] torch: {torch.__version__}\")\n",
        "print(f\"[OK] numpy: {np.__version__}\")\n",
        "print(f\"[OK] CUDA: {torch.cuda.is_available()}\")\n",
        "\n",
        "if torch.cuda.is_available():\n",
        "    print(f\"[OK] GPU: {torch.cuda.get_device_name(0)}\")\n",
        "    print(f\"[OK] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB\")\n",
        "\n",
        "# Test unsloth import\n",
        "print(\"\\n[INFO] Testing unsloth import...\")\n",
        "from unsloth import FastLanguageModel\n",
        "print(\"[OK] Unsloth imported successfully!\")"
    ]
}

# ============================================================================
# CELL 3: Load Model
# ============================================================================
cell_3_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 3. Load Model\n",
        "\n",
        "Loading `gemma-2-2b-it` in 4-bit (~5GB VRAM)"
    ]
}

cell_3_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Configuration\n",
        "MODEL_NAME = \"unsloth/gemma-2-2b-it-bnb-4bit\"\n",
        "MAX_SEQ_LENGTH = 2048\n",
        "DTYPE = None\n",
        "LOAD_IN_4BIT = True\n",
        "\n",
        "print(f\"[INFO] Loading {MODEL_NAME}...\")\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name=MODEL_NAME,\n",
        "    max_seq_length=MAX_SEQ_LENGTH,\n",
        "    dtype=DTYPE,\n",
        "    load_in_4bit=LOAD_IN_4BIT,\n",
        ")\n",
        "\n",
        "print(f\"\\n[OK] Model loaded!\")\n",
        "print(f\"[OK] VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB\")"
    ]
}

# ============================================================================
# CELL 4: LoRA Adapters
# ============================================================================
cell_4_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 4. Add LoRA Adapters"
    ]
}

cell_4_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "model = FastLanguageModel.get_peft_model(\n",
        "    model,\n",
        "    r=16,\n",
        "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n",
        "                    \"gate_proj\", \"up_proj\", \"down_proj\"],\n",
        "    lora_alpha=16,\n",
        "    lora_dropout=0,\n",
        "    bias=\"none\",\n",
        "    use_gradient_checkpointing=\"unsloth\",\n",
        "    random_state=3407,\n",
        ")\n",
        "\n",
        "print(\"[OK] LoRA adapters added!\")\n",
        "model.print_trainable_parameters()"
    ]
}

# ============================================================================
# CELL 5: Load Dataset
# ============================================================================
cell_5_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 5. Load Dataset"
    ]
}

cell_5_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "from datasets import load_dataset\n",
        "import glob\n",
        "\n",
        "# Find dataset\n",
        "paths = [\"/kaggle/input/audit-dataset/audit_dataset.jsonl\",\n",
        "         \"/kaggle/input/*/audit_dataset.jsonl\",\n",
        "         \"/kaggle/input/*/*.jsonl\"]\n",
        "\n",
        "dataset_path = None\n",
        "for p in paths:\n",
        "    m = glob.glob(p)\n",
        "    if m: dataset_path = m[0]; break\n",
        "\n",
        "if not dataset_path:\n",
        "    raise FileNotFoundError(\"Upload audit_dataset.jsonl to Kaggle Input!\")\n",
        "\n",
        "print(f\"[INFO] Loading: {dataset_path}\")\n",
        "dataset = load_dataset(\"json\", data_files=dataset_path, split=\"train\")\n",
        "\n",
        "# Alpaca format\n",
        "ALPACA = \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n",
        "\n",
        "### Instruction:\n",
        "{}\n",
        "\n",
        "### Response:\n",
        "{}\"\"\"\n",
        "\n",
        "EOS = tokenizer.eos_token\n",
        "\n",
        "def fmt(ex):\n",
        "    return {\"text\": [ALPACA.format(i, o) + EOS for i, o in zip(ex[\"instruction\"], ex[\"output\"])]}\n",
        "\n",
        "dataset = dataset.map(fmt, batched=True)\n",
        "print(f\"[OK] Loaded {len(dataset)} examples\")"
    ]
}

# ============================================================================
# CELL 6: Train
# ============================================================================
cell_6_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 6. Train (~25 min)"
    ]
}

cell_6_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "from transformers import TrainingArguments\n",
        "from trl import SFTTrainer\n",
        "\n",
        "trainer = SFTTrainer(\n",
        "    model=model,\n",
        "    tokenizer=tokenizer,\n",
        "    train_dataset=dataset,\n",
        "    dataset_text_field=\"text\",\n",
        "    max_seq_length=MAX_SEQ_LENGTH,\n",
        "    dataset_num_proc=2,\n",
        "    packing=False,\n",
        "    args=TrainingArguments(\n",
        "        output_dir=\"./outputs\",\n",
        "        per_device_train_batch_size=2,\n",
        "        gradient_accumulation_steps=4,\n",
        "        warmup_steps=5,\n",
        "        max_steps=100,\n",
        "        learning_rate=2e-4,\n",
        "        fp16=not torch.cuda.is_bf16_supported(),\n",
        "        bf16=torch.cuda.is_bf16_supported(),\n",
        "        logging_steps=10,\n",
        "        optim=\"adamw_8bit\",\n",
        "        weight_decay=0.01,\n",
        "        lr_scheduler_type=\"linear\",\n",
        "        seed=3407,\n",
        "        report_to=\"none\",\n",
        "    ),\n",
        ")\n",
        "\n",
        "print(\"[INFO] Training... (~25 min)\")\n",
        "stats = trainer.train()\n",
        "print(f\"\\n[OK] Done in {stats.metrics['train_runtime']:.0f}s\")"
    ]
}

# ============================================================================
# CELL 7: Save
# ============================================================================
cell_7_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 7. Save Model"
    ]
}

cell_7_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Test inference\n",
        "FastLanguageModel.for_inference(model)\n",
        "test = \"Analyze test coverage: 330 files, 5 executable, 0% coverage\"\n",
        "inputs = tokenizer([ALPACA.format(test, \"\")], return_tensors=\"pt\").to(\"cuda\")\n",
        "out = model.generate(**inputs, max_new_tokens=256, use_cache=True)\n",
        "print(\"[TEST]\\n\", tokenizer.decode(out[0]))\n",
        "\n",
        "# Save\n",
        "model.save_pretrained(\"audit-gemma-v1\")\n",
        "tokenizer.save_pretrained(\"audit-gemma-v1\")\n",
        "print(\"\\n[OK] Saved to audit-gemma-v1/\")"
    ]
}

# ============================================================================
# BUILD
# ============================================================================
notebook['cells'] = [
    cell_0_markdown,
    cell_1_markdown, cell_1_code,
    cell_2_markdown, cell_2_code,
    cell_3_markdown, cell_3_code,
    cell_4_markdown, cell_4_code,
    cell_5_markdown, cell_5_code,
    cell_6_markdown, cell_6_code,
    cell_7_markdown, cell_7_code,
]

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("[OK] Notebook fixed!")
print("\n[KEY FIXES]")
print("  1. Use --force-reinstall numpy (binary compatible)")
print("  2. Added KERNEL RESTART instruction")
print("  3. Separate verify cell after restart")
print("\n[WORKFLOW]")
print("  Cell 1: Install -> RESTART KERNEL")
print("  Cell 2: Verify (skip Cell 1)")
print("  Cell 3-7: Train")
