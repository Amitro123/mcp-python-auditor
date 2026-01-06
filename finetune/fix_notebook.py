"""
FINAL FIX - Uninstall torchao which causes torch.int1 error
torchao is optional and causes version conflicts
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
        "**Production Notebook** | 2026 | ~25 min training\n",
        "\n",
        "**Workflow:**\n",
        "1. Run Cell 1 (Install) → RESTART KERNEL\n",
        "2. Run Cells 2-7 (skip Cell 1)"
    ]
}

# ============================================================================
# CELL 1: Install - COMPLETE FIX
# ============================================================================
cell_1_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 1. Install (then RESTART KERNEL!)"
    ]
}

# FINAL E2E FIX - BASED ON WORKING AMITROSEN PROJECTS
# Strategy: Use the exact stack from qwen3-phone-deploy.ipynb (datasets 4.2.0, transformers 4.45.0+)

cell_1_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# KAGGLE UNSLOTH STABLE INSTALL (2026)\n",
        "# Based on working config from qwen3-phone-deploy.ipynb\n",
        "\n",
        "import subprocess\n",
        "import sys\n",
        "\n",
        "def run_pip(cmd, msg):\n",
        "    print(msg)\n",
        "    # Using --no-cache-dir to ensure fresh binaries\n",
        "    full_cmd = f\"pip install -q --no-cache-dir {cmd}\"\n",
        "    subprocess.run(full_cmd, shell=True, capture_output=True)\n",
        "\n",
        "print(\"=\"*60)\n",
        "print(\"🚀 KAGGLE UNSLOTH STABLE INSTALL\")\n",
        "print(\"=\"*60)\n",
        "\n",
        "print(\"[1/5] Cleaning environment...\")\n",
        "subprocess.run(\"pip uninstall -y torchao unsloth unsloth_zoo transformers -q\", shell=True)\n",
        "\n",
        "run_pip(\n",
        "    \"fsspec==2024.9.0 datasets==4.2.0 huggingface_hub>=0.23.0\", \n",
        "    \"[2/5] Installing base deps (fsspec 2024.9.0, datasets 4.2.0)...\"\n",
        ")\n",
        "\n",
        "run_pip(\n",
        "    \"peft accelerate bitsandbytes trl transformers>=4.45.0\",\n",
        "    \"[3/5] Installing training components (transformers >= 4.45.0)...\"\n",
        ")\n",
        "\n",
        "run_pip(\n",
        "    '\"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"',\n",
        "    \"[4/5] Installing Unsloth (GitHub Latest)...\"\n",
        ")\n",
        "\n",
        "run_pip(\"xformers==0.0.28.post3\", \"[5/5] Installing xformers...\")\n",
        "\n",
        "print(\"\\n\" + \"=\"*60)\n",
        "print(\"✅ INSTALLATION COMPLETE!\")\n",
        "print(\"=\"*60)\n",
        "print(\"\\n\" + \"*\"*60)\n",
        "print(\"*** IMPORTANT: RESTART KERNEL NOW! ***\")\n",
        "print(\"*** Then run the cells below in order. ***\")\n",
        "print(\"*\"*60)\n"
    ]
}

# ============================================================================
# CELL 2: Load Model (Import unsloth FIRST)
# ============================================================================
cell_2_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 2. Load Model\n",
        "\n",
        "**Crucial:** Import `unsloth` before anything else!"
    ]
}

cell_2_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import unsloth  # Must be first!\n",
        "import torch\n",
        "from unsloth import FastLanguageModel\n",
        "\n",
        "print(f\"✅ Unsloth: {unsloth.__version__}\")\n",
        "print(f\"✅ Torch: {torch.__version__}\")\n",
        "\n",
        "# Configuration\n",
        "MODEL_NAME = \"unsloth/gemma-2-2b-it-bnb-4bit\"\n",
        "MAX_SEQ_LENGTH = 2048\n",
        "LOAD_IN_4BIT = True\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name=MODEL_NAME,\n",
        "    max_seq_length=MAX_SEQ_LENGTH,\n",
        "    dtype=None,  # Auto-detect\n",
        "    load_in_4bit=LOAD_IN_4BIT,\n",
        ")"
    ]
}

# ============================================================================
# CELL 3: Load Model
# ============================================================================
cell_3_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 3. Load Model"
    ]
}

cell_3_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "MODEL_NAME = \"unsloth/gemma-2-2b-it-bnb-4bit\"\n",
        "MAX_SEQ_LENGTH = 2048\n",
        "\n",
        "print(f\"[INFO] Loading {MODEL_NAME}...\")\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name=MODEL_NAME,\n",
        "    max_seq_length=MAX_SEQ_LENGTH,\n",
        "    dtype=None,\n",
        "    load_in_4bit=True,\n",
        ")\n",
        "\n",
        "print(f\"\\n[OK] Model loaded!\")\n",
        "print(f\"[OK] VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB\")"
    ]
}

# ============================================================================
# CELL 4: LoRA
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
        "print(\"[OK] LoRA added!\")\n",
        "model.print_trainable_parameters()"
    ]
}

# ============================================================================
# CELL 5: Dataset
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
        "for p in [\"/kaggle/input/audit-dataset/audit_dataset.jsonl\",\n",
        "          \"/kaggle/input/*/audit_dataset.jsonl\",\n",
        "          \"/kaggle/input/*/*.jsonl\"]:\n",
        "    m = glob.glob(p)\n",
        "    if m:\n",
        "        dataset_path = m[0]\n",
        "        break\n",
        "else:\n",
        "    raise FileNotFoundError(\"Upload audit_dataset.jsonl!\")\n",
        "\n",
        "print(f\"[INFO] Loading: {dataset_path}\")\n",
        "dataset = load_dataset(\"json\", data_files=dataset_path, split=\"train\")\n",
        "\n",
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
        "print(f\"[OK] {len(dataset)} examples\")"
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
        "print(\"[INFO] Training...\")\n",
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
        "# Test\n",
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

print("[OK] FINAL E2E FIX APPLIED!")
print("\n[FIXES APPLIED - KAGGLE STABLE 2026]")
print("  1. CLEAN ENVIRONMENT (Uninstall torchao, unsloth, zoo)")
print("  2. PIN datasets==4.2.0 (Stable version from working projects)")
print("  3. UPGRADE transformers>=4.45.0 (Fixes Unpack error)")
print("  4. USE unsloth[colab-new] (Latest GitHub optimizations)")
print("  5. IMPORT unsloth FIRST in Model Load cell")
print("\n[WORKFLOW]")
print("  1. Run Cell 1 -> RESTART KERNEL")
print("  2. Run Cell 2 (Model Load) -> Success")
