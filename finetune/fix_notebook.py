"""
Production Kaggle Notebook Generator for Unsloth Gemma-2-2b Fine-tuning
Optimized for: Kaggle Tesla T4, Python 3.12, torch 2.4.1+cu121 (2026)
"""

import json

# Read the existing notebook
notebook_path = 'finetune/kaggle_finetune.ipynb'
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# ============================================================================
# CELL 0: Title Markdown
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
        "| Train Time | ~25 min |\n",
        "| Dataset | 100 audit examples |\n",
        "\n",
        "**Setup:** Upload `audit_dataset.jsonl` to Kaggle Input"
    ]
}

# ============================================================================
# CELL 1: Install Dependencies (Ultra-Clean)
# ============================================================================
cell_1_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 1. Install Dependencies\n",
        "\n",
        "Ultra-clean install - works with Kaggle's pre-installed torch 2.4.1+cu121"
    ]
}

cell_1_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# KAGGLE UNSLOTH INSTALL (2026 STABLE)\n",
        "# Works with pre-installed torch 2.4.1+cu121\n",
        "\n",
        "import subprocess\n",
        "import sys\n",
        "\n",
        "def run_quiet(cmd):\n",
        "    \"\"\"Run pip command, show only errors\"\"\"\n",
        "    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)\n",
        "    if result.returncode != 0:\n",
        "        print(f\"[WARN] {result.stderr[-500:] if result.stderr else 'Unknown error'}\")\n",
        "    return result.returncode == 0\n",
        "\n",
        "print(\"[1/4] Installing numpy 1.26.4 (compatibility fix)...\")\n",
        "run_quiet(\"pip install -q numpy==1.26.4\")\n",
        "\n",
        "print(\"[2/4] Installing Unsloth + unsloth_zoo...\")\n",
        "run_quiet('pip install -q \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"')\n",
        "run_quiet('pip install -q unsloth_zoo')\n",
        "\n",
        "print(\"[3/4] Installing training dependencies...\")\n",
        "run_quiet(\"pip install -q trl==0.9.6 peft accelerate bitsandbytes datasets\")\n",
        "\n",
        "print(\"[4/4] Installing xformers (pre-built)...\")\n",
        "run_quiet(\"pip install -q xformers==0.0.27.post2\")\n",
        "\n",
        "print(\"\\n\" + \"=\"*50)\n",
        "print(\"[OK] Installation complete!\")\n",
        "print(\"=\"*50)\n",
        "\n",
        "# Verify\n",
        "import torch\n",
        "print(f\"\\n[OK] torch: {torch.__version__}\")\n",
        "print(f\"[OK] CUDA: {torch.cuda.is_available()}\")\n",
        "if torch.cuda.is_available():\n",
        "    print(f\"[OK] GPU: {torch.cuda.get_device_name(0)}\")\n",
        "    print(f\"[OK] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB\")"
    ]
}

# ============================================================================
# CELL 2: Load Model + Tokenizer
# ============================================================================
cell_2_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 2. Load Model\n",
        "\n",
        "Loading `gemma-2-2b-it` in 4-bit quantization (~5GB VRAM)"
    ]
}

cell_2_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import torch\n",
        "from unsloth import FastLanguageModel\n",
        "\n",
        "# Configuration\n",
        "MODEL_NAME = \"unsloth/gemma-2-2b-it-bnb-4bit\"\n",
        "MAX_SEQ_LENGTH = 2048\n",
        "DTYPE = None  # Auto-detect (float16 on T4)\n",
        "LOAD_IN_4BIT = True\n",
        "\n",
        "print(f\"[INFO] Loading {MODEL_NAME}...\")\n",
        "print(f\"[INFO] Sequence length: {MAX_SEQ_LENGTH}\")\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name=MODEL_NAME,\n",
        "    max_seq_length=MAX_SEQ_LENGTH,\n",
        "    dtype=DTYPE,\n",
        "    load_in_4bit=LOAD_IN_4BIT,\n",
        ")\n",
        "\n",
        "print(f\"\\n[OK] Model loaded successfully!\")\n",
        "print(f\"[OK] VRAM used: {torch.cuda.memory_allocated() / 1e9:.2f} GB\")"
    ]
}

# ============================================================================
# CELL 3: Add LoRA Adapters
# ============================================================================
cell_3_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 3. Add LoRA Adapters\n",
        "\n",
        "LoRA config: r=16, targeting all attention + MLP layers"
    ]
}

cell_3_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# LoRA Configuration\n",
        "LORA_R = 16\n",
        "LORA_ALPHA = 16\n",
        "LORA_DROPOUT = 0\n",
        "TARGET_MODULES = [\n",
        "    \"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",  # Attention\n",
        "    \"gate_proj\", \"up_proj\", \"down_proj\"       # MLP\n",
        "]\n",
        "\n",
        "print(f\"[INFO] Adding LoRA adapters (r={LORA_R})...\")\n",
        "\n",
        "model = FastLanguageModel.get_peft_model(\n",
        "    model,\n",
        "    r=LORA_R,\n",
        "    target_modules=TARGET_MODULES,\n",
        "    lora_alpha=LORA_ALPHA,\n",
        "    lora_dropout=LORA_DROPOUT,\n",
        "    bias=\"none\",\n",
        "    use_gradient_checkpointing=\"unsloth\",\n",
        "    random_state=3407,\n",
        ")\n",
        "\n",
        "print(\"\\n[OK] LoRA adapters added!\")\n",
        "model.print_trainable_parameters()"
    ]
}

# ============================================================================
# CELL 4: Load Dataset
# ============================================================================
cell_4_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 4. Load Audit Dataset\n",
        "\n",
        "Loading `audit_dataset.jsonl` with Alpaca prompt format"
    ]
}

cell_4_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "from datasets import load_dataset\n",
        "import glob\n",
        "\n",
        "# Find dataset in Kaggle input folders\n",
        "DATASET_PATHS = [\n",
        "    \"/kaggle/input/audit-dataset/audit_dataset.jsonl\",\n",
        "    \"/kaggle/input/*/audit_dataset.jsonl\",\n",
        "    \"/kaggle/input/*/*.jsonl\",\n",
        "]\n",
        "\n",
        "dataset_path = None\n",
        "for pattern in DATASET_PATHS:\n",
        "    matches = glob.glob(pattern)\n",
        "    if matches:\n",
        "        dataset_path = matches[0]\n",
        "        break\n",
        "\n",
        "if not dataset_path:\n",
        "    raise FileNotFoundError(\n",
        "        \"Dataset not found! Upload audit_dataset.jsonl to Kaggle Input.\"\n",
        "    )\n",
        "\n",
        "print(f\"[INFO] Loading dataset from: {dataset_path}\")\n",
        "dataset = load_dataset(\"json\", data_files=dataset_path, split=\"train\")\n",
        "\n",
        "# Alpaca prompt template\n",
        "ALPACA_PROMPT = \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n",
        "\n",
        "### Instruction:\n",
        "{}\n",
        "\n",
        "### Response:\n",
        "{}\"\"\"\n",
        "\n",
        "EOS_TOKEN = tokenizer.eos_token\n",
        "\n",
        "def format_prompt(examples):\n",
        "    texts = []\n",
        "    for instruction, output in zip(examples[\"instruction\"], examples[\"output\"]):\n",
        "        text = ALPACA_PROMPT.format(instruction, output) + EOS_TOKEN\n",
        "        texts.append(text)\n",
        "    return {\"text\": texts}\n",
        "\n",
        "print(\"[INFO] Formatting dataset...\")\n",
        "dataset = dataset.map(format_prompt, batched=True)\n",
        "\n",
        "print(f\"\\n[OK] Loaded {len(dataset)} examples\")\n",
        "print(f\"[SAMPLE] {dataset[0]['text'][:200]}...\")"
    ]
}

# ============================================================================
# CELL 5: Train Model
# ============================================================================
cell_5_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 5. Train Model\n",
        "\n",
        "SFTTrainer with Unsloth optimization (~25 min on T4)"
    ]
}

cell_5_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "from transformers import TrainingArguments\n",
        "from trl import SFTTrainer\n",
        "\n",
        "# Training configuration (optimized for T4 GPU)\n",
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
        "        report_to=\"none\",  # Disable wandb\n",
        "    ),\n",
        ")\n",
        "\n",
        "print(\"[INFO] Starting training...\")\n",
        "print(\"[INFO] Expected time: ~25 minutes\")\n",
        "print(\"=\"*50)\n",
        "\n",
        "trainer_stats = trainer.train()\n",
        "\n",
        "print(\"\\n\" + \"=\"*50)\n",
        "print(\"[OK] Training complete!\")\n",
        "print(f\"[OK] Time: {trainer_stats.metrics['train_runtime']:.1f}s\")\n",
        "print(f\"[OK] Samples/sec: {trainer_stats.metrics['train_samples_per_second']:.2f}\")"
    ]
}

# ============================================================================
# CELL 6: Save Model + Push to HuggingFace
# ============================================================================
cell_6_markdown = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 6. Save Model\n",
        "\n",
        "Save locally + optionally push to HuggingFace Hub"
    ]
}

cell_6_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Test inference first\n",
        "print(\"[INFO] Testing inference...\")\n",
        "FastLanguageModel.for_inference(model)\n",
        "\n",
        "test_prompt = \"Analyze test coverage: 330 files found, 5 executable, 0% coverage\"\n",
        "inputs = tokenizer(\n",
        "    [ALPACA_PROMPT.format(test_prompt, \"\")],\n",
        "    return_tensors=\"pt\"\n",
        ").to(\"cuda\")\n",
        "\n",
        "outputs = model.generate(**inputs, max_new_tokens=256, use_cache=True)\n",
        "result = tokenizer.batch_decode(outputs)[0]\n",
        "\n",
        "print(\"\\n[INFERENCE TEST]\")\n",
        "print(result)\n",
        "\n",
        "# Save locally\n",
        "print(\"\\n\" + \"=\"*50)\n",
        "print(\"[INFO] Saving model...\")\n",
        "model.save_pretrained(\"audit-gemma-v1\")\n",
        "tokenizer.save_pretrained(\"audit-gemma-v1\")\n",
        "print(\"[OK] Model saved to 'audit-gemma-v1/'\")\n",
        "\n",
        "# Optional: Push to HuggingFace\n",
        "# Uncomment to push (requires HF_TOKEN in Kaggle secrets)\n",
        "'''\n",
        "from huggingface_hub import login\n",
        "import os\n",
        "\n",
        "HF_TOKEN = os.environ.get(\"HF_TOKEN\") or \"YOUR_TOKEN_HERE\"\n",
        "login(token=HF_TOKEN)\n",
        "\n",
        "model.push_to_hub(\"amitrosen/audit-gemma-v1\", token=HF_TOKEN)\n",
        "tokenizer.push_to_hub(\"amitrosen/audit-gemma-v1\", token=HF_TOKEN)\n",
        "print(\"[OK] Pushed to HuggingFace!\")\n",
        "'''\n",
        "\n",
        "print(\"\\n\" + \"=\"*50)\n",
        "print(\"[DONE] Fine-tuning complete!\")\n",
        "print(\"Download 'audit-gemma-v1/' from Kaggle Output\")\n",
        "print(\"=\"*50)"
    ]
}

# ============================================================================
# BUILD NOTEBOOK
# ============================================================================
new_cells = [
    cell_0_markdown,
    cell_1_markdown,
    cell_1_code,
    cell_2_markdown,
    cell_2_code,
    cell_3_markdown,
    cell_3_code,
    cell_4_markdown,
    cell_4_code,
    cell_5_markdown,
    cell_5_code,
    cell_6_markdown,
    cell_6_code,
]

notebook['cells'] = new_cells

# Save
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("[OK] Notebook rebuilt with 6 production cells!")
print("\nCells:")
print("  1. Install Dependencies (Ultra-Clean)")
print("  2. Load Model + Tokenizer")
print("  3. Add LoRA Adapters")
print("  4. Load Audit Dataset")
print("  5. Train Model (SFTTrainer)")
print("  6. Save + Push to HuggingFace")
