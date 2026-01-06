"""
CLEAN FINAL FIX - Kaggle Unsloth Stable 2026
Implements the exact working configuration from Amit's Qwen3 notebook.
"""

import json

notebook_path = 'finetune/kaggle_finetune.ipynb'
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# --- CELL 0: Title ---
cell_0 = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# Fine-tune Gemma-2-2b for Code Audit (Kaggle T4)\n",
        "\n",
        "**Stable Production Edition (2026)**\n",
        "\n",
        "| | |\n",
        "|---|---|\n",
        "| 🤖 Model | `unsloth/gemma-2-2b-it-bnb-4bit` |\n",
        "| ⚡ Framework | Unsloth (Stable GitHub Version) |\n",
        "| ⏱️ Runtime | ~30 min |\n"
    ]
}

# --- CELL 1: Install ---
cell_1_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 1. Install Dependencies (Nuclear Clean)"]
}

cell_1_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "# KAGGLE UNSLOTH STABLE INSTALL (2026)\n",
        "import subprocess\n",
        "\n",
        "def run_pip(cmd, msg):\n",
        "    print(msg)\n",
        "    subprocess.run(f\"pip install -q --no-cache-dir {cmd}\", shell=True, capture_output=True)\n",
        "\n",
        "print(\"=\"*60)\n",
        "print(\"🚀 CLEANING & INSTALLING STABLE STACK\")\n",
        "print(\"=\"*60)\n",
        "\n",
        "subprocess.run(\"pip uninstall -y torchao unsloth unsloth_zoo transformers -q\", shell=True)\n",
        "\n",
        "run_pip(\"fsspec==2024.9.0 datasets==4.2.0 huggingface_hub>=0.23.0\", \"[1/4] Installing base deps...\")\n",
        "run_pip(\"peft accelerate bitsandbytes trl transformers>=4.45.0\", \"[2/4] Installing transformers 4.45+...\")\n",
        "run_pip('\"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"', \"[3/4] Installing Unsloth...\")\n",
        "run_pip(\"xformers==0.0.28.post3\", \"[4/4] Installing xformers...\")\n",
        "\n",
        "print(\"\\n✅ DONE! RESTART KERNEL NOW! Then run Cell 2.\")\n"
    ]
}

# --- CELL 2: Load Model ---
cell_2_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 2. Load Model\n\n**Crucial:** Import `unsloth` before anything else."]
}

cell_2_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "import unsloth  # Must be first!\n",
        "import torch\n",
        "from unsloth import FastLanguageModel\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name=\"unsloth/gemma-2-2b-it-bnb-4bit\",\n",
        "    max_seq_length=2048,\n",
        "    dtype=None,\n",
        "    load_in_4bit=True,\n",
        ")\n",
        "print(\"✅ Model loaded!\")\n"
    ]
}

# --- CELL 3: LoRA ---
cell_3_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 3. Add LoRA Adapters"]
}

cell_3_code = {
    "cell_type": "code",
    "metadata": {},
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
        "model.print_trainable_parameters()\n"
    ]
}

# --- CELL 4: Dataset ---
cell_4_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 4. Load Dataset"]
}

cell_4_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "from datasets import load_dataset\n",
        "import glob\n",
        "\n",
        "for p in [\"/kaggle/input/audit-dataset/audit_dataset.jsonl\",\n",
        "          \"/kaggle/input/*/audit_dataset.jsonl\",\n",
        "          \"/kaggle/input/*/*.jsonl\"]:\n",
        "    m = glob.glob(p)\n",
        "    if m: dataset_path = m[0]; break\n",
        "else: raise FileNotFoundError(\"Upload audit_dataset.jsonl!\")\n",
        "\n",
        "dataset = load_dataset(\"json\", data_files=dataset_path, split=\"train\")\n",
        "ALPACA = \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\\n### Instruction:\\n{}\\n\\n### Response:\\n{}\"\"\"\n",
        "EOS = tokenizer.eos_token\n",
        "dataset = dataset.map(lambda x: {\"text\": [ALPACA.format(i, o) + EOS for i, o in zip(x[\"instruction\"], x[\"output\"])]}, batched=True)\n",
        "print(f\"✅ Loaded {len(dataset)} examples\")\n"
    ]
}

# --- CELL 5: Train ---
cell_5_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 5. Fine-tune (~30 min)"]
}

cell_5_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "from transformers import TrainingArguments\n",
        "from trl import SFTTrainer\n",
        "\n",
        "trainer = SFTTrainer(\n",
        "    model=model,\n",
        "    tokenizer=tokenizer,\n",
        "    train_dataset=dataset,\n",
        "    dataset_text_field=\"text\",\n",
        "    max_seq_length=2048,\n",
        "    dataset_num_proc=2,\n",
        "    args=TrainingArguments(\n",
        "        output_dir=\"./outputs\",\n",
        "        per_device_train_batch_size=2,\n",
        "        gradient_accumulation_steps=4,\n",
        "        max_steps=100,\n",
        "        learning_rate=2e-4,\n",
        "        fp16=not torch.cuda.is_bf16_supported(),\n",
        "        bf16=torch.cuda.is_bf16_supported(),\n",
        "        logging_steps=10,\n",
        "        optim=\"adamw_8bit\",\n",
        "        seed=3407,\n",
        "        report_to=\"none\",\n",
        "    ),\n",
        ")\n",
        "trainer.train()\n"
    ]
}

# --- CELL 6: Save ---
cell_6_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": ["## 6. Save Model"]
}

cell_6_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "model.save_pretrained(\"audit-gemma-v1\")\n",
        "tokenizer.save_pretrained(\"audit-gemma-v1\")\n",
        "print(\"✅ Saved to audit-gemma-v1/\")\n"
    ]
}

# Assembly
notebook['cells'] = [
    cell_0, 
    cell_1_md, cell_1_code,
    cell_2_md, cell_2_code,
    cell_3_md, cell_3_code,
    cell_4_md, cell_4_code,
    cell_5_md, cell_5_code,
    cell_6_md, cell_6_code
]

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("✅ Notebook Rebuilt Successfully (Clean & Stable)")
