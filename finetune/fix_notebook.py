import json
import os

notebook_path = 'finetune/kaggle_finetune.ipynb'

# --- Notebook Structure ---
notebook = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

# --- CELL 0: Title ---
cell_0 = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "# Fine-tune Gemma-2-2b (Self-Healing Edition)\n",
        "\n",
        "**Instructions:**\n",
        "1. Click **`Run All`**.\n",
        "2. The first cell will auto-restart the kernel once.\n",
        "3. Training will start automatically after the self-restart."
    ]
}

# --- CELL 1: THE MAGIC CELL ---
cell_1_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "# MAGIC CELL: Install -> Auto-Restart -> Load\n",
        "import os, sys, subprocess, time\n",
        "\n",
        "def is_env_ready():\n",
        "    try:\n",
        "        import unsloth, torch, torchvision\n",
        "        from transformers.processing_utils import Unpack\n",
        "        return True\n",
        "    except:\n",
        "        return False\n",
        "\n",
        "if not is_env_ready():\n",
        "    print('🚀 Step 1: Installing stable environment...')\n",
        "    subprocess.run('pip uninstall -y torchao unsloth unsloth_zoo transformers -q', shell=True)\n",
        "    \n",
        "    pkgs = [\n",
        "        'torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121',\n",
        "        'fsspec==2024.9.0 datasets==4.2.0',\n",
        "        'transformers>=4.45.0 peft accelerate bitsandbytes trl',\n",
        "        '\"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"',\n",
        "        'xformers==0.0.28.post3'\n",
        "    ]\n",
        "    \n",
        "    for pkg in pkgs:\n",
        "        print(f'   Installing {pkg.split(\" \")[0]}...')\n",
        "        subprocess.run(f'pip install -q --no-cache-dir {pkg}', shell=True)\n",
        "\n",
        "    print('\\n✅ Setup complete! Auto-restarting...')\n",
        "    os._exit(0)\n",
        "\n",
        "import unsloth, torch\n",
        "from unsloth import FastLanguageModel\n",
        "print('✅ Environment Ready!')\n",
        "\n",
        "model, tokenizer = FastLanguageModel.from_pretrained(\n",
        "    model_name='unsloth/gemma-2-2b-it-bnb-4bit',\n",
        "    max_seq_length=2048,\n",
        "    dtype=None,\n",
        "    load_in_4bit=True,\n",
        ")\n",
        "print('✅ Model Loaded!')"
    ]
}

# --- CELL 2: LoRA ---
cell_2_code = {
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
        "model.print_trainable_parameters()"
    ]
}

# --- CELL 3: Dataset ---
cell_3_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "from datasets import load_dataset\n",
        "import glob\n",
        "for p in [\"/kaggle/input/audit-dataset/audit_dataset.jsonl\", \"/kaggle/input/*/audit_dataset.jsonl\"]:\n",
        "    m = glob.glob(p)\n",
        "    if m: dataset_path = m[0]; break\n",
        "else: dataset_path = \"audit_dataset.jsonl\"\n",
        "\n",
        "dataset = load_dataset(\"json\", data_files=dataset_path, split=\"train\")\n",
        "ALPACA = \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{}\\n\\n### Response:\n{}\"\"\"\n",
        "dataset = dataset.map(lambda x: {\n",
        "    \"text\": [ALPACA.format(i, o) + tokenizer.eos_token for i, o in zip(x['instruction'], x['output'])]\n",
        "}, batched=True)\n",
        "print(f'✅ Loaded {len(dataset)} examples')"
    ]
}

# --- CELL 4: Train ---
cell_4_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "from transformers import TrainingArguments\n",
        "from trl import SFTTrainer\n",
        "trainer = SFTTrainer(\n",
        "    model=model,\n",
        "    tokenizer=tokenizer,\n",
        "    train_dataset=dataset,\n",
        "    dataset_text_field=\"text\",\n",
        "    max_seq_length=2048,\n",
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
        "        report_to=\"none\",\n",
        "    ),\n",
        ")\n",
        "trainer.train()"
    ]
}

# --- CELL 5: Save ---
cell_5_code = {
    "cell_type": "code",
    "metadata": {},
    "source": [
        "model.save_pretrained(\"audit-gemma-v1\")\n",
        "tokenizer.save_pretrained(\"audit-gemma-v1\")\n",
        "print(\"✅ Saved to audit-gemma-v1/\")"
    ]
}

# Assembly
notebook['cells'] = [cell_0, cell_1_code, cell_2_code, cell_3_code, cell_4_code, cell_5_code]

# Normalize source to lists of lines ending with \n
for cell in notebook['cells']:
    lines = []
    for line in cell['source']:
        if not line.endswith('\n'):
            lines.append(line + '\n')
        else:
            lines.append(line)
    cell['source'] = lines

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)

print("[OK] Notebook Rebuilt (Fixed SyntaxError)")
