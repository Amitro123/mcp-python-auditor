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

# THE COMPLETE FIX - uninstall torchao + proper versions
cell_1_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# KAGGLE UNSLOTH E2E FIX - 2026\n",
        "# Fixes: torch._inductor.config, numpy binary, torch.int1 (torchao)\n",
        "\n",
        "import subprocess\n",
        "\n",
        "def run(cmd, msg=\"\"):\n",
        "    if msg: print(msg)\n",
        "    subprocess.run(cmd, shell=True, capture_output=True)\n",
        "\n",
        "print(\"=\"*60)\n",
        "print(\"KAGGLE UNSLOTH COMPLETE INSTALL\")\n",
        "print(\"=\"*60)\n",
        "\n",
        "# Step 1: Uninstall conflicting packages\n",
        "run(\"pip uninstall -y torchao -q\", \"[1/6] Removing torchao (causes torch.int1 error)...\")\n",
        "\n",
        "# Step 2: Upgrade PyTorch\n",
        "run(\n",
        "    \"pip install -q torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121\",\n",
        "    \"[2/6] Installing PyTorch 2.5.1...\"\n",
        ")\n",
        "\n",
        "# Step 3: Force reinstall numpy\n",
        "run(\"pip install -q --force-reinstall numpy\", \"[3/6] Reinstalling numpy...\")\n",
        "\n",
        "# Step 4: Install Unsloth\n",
        "run(\n",
        "    'pip install -q \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"',\n",
        "    \"[4/6] Installing Unsloth...\"\n",
        ")\n",
        "run(\"pip install -q unsloth_zoo\", \"     + unsloth_zoo...\")\n",
        "\n",
        "# Step 5: Training deps (pin transformers to avoid torchao)\n",
        "run(\n",
        "    \"pip install -q trl==0.9.6 peft accelerate bitsandbytes datasets transformers==4.44.2\",\n",
        "    \"[5/6] Installing training dependencies...\"\n",
        ")\n",
        "\n",
        "# Step 6: xformers\n",
        "run(\"pip install -q xformers==0.0.28.post3\", \"[6/6] Installing xformers...\")\n",
        "\n",
        "# Verify torchao is gone\n",
        "result = subprocess.run(\"pip show torchao\", shell=True, capture_output=True)\n",
        "torchao_status = \"REMOVED\" if result.returncode != 0 else \"WARNING: Still installed!\"\n",
        "\n",
        "print(\"\\n\" + \"=\"*60)\n",
        "print(\"[OK] Installation complete!\")\n",
        "print(f\"[OK] torchao: {torchao_status}\")\n",
        "print(\"=\"*60)\n",
        "print(\"\\n\" + \"*\"*60)\n",
        "print(\"***  RESTART KERNEL NOW!  ***\")\n",
        "print(\"***  Then run Cell 2 (skip this cell)  ***\")\n",
        "print(\"*\"*60)"
    ]
}

# ============================================================================
# CELL 2: Verify (after restart)
# ============================================================================
cell_2_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 2. Verify (run after kernel restart)"
    ]
}

cell_2_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# MUST import unsloth FIRST (before transformers)\n",
        "import unsloth\n",
        "\n",
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
        "from unsloth import FastLanguageModel\n",
        "print(\"\\n[OK] Unsloth imported successfully!\")"
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
print("\n[FIXES APPLIED]")
print("  1. UNINSTALL torchao (causes torch.int1 error)")
print("  2. Pin transformers==4.44.2 (avoids torchao import)")
print("  3. Import unsloth FIRST in Cell 2 (before transformers)")
print("  4. Force reinstall numpy (binary fix)")
print("  5. Upgrade torch 2.4.0 -> 2.5.1")
print("\n[WORKFLOW]")
print("  1. Run Cell 1 -> RESTART KERNEL")
print("  2. Run Cells 2-7 (skip Cell 1)")
