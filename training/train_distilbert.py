"""
DistilBERT Fine-Tuning for InvisiPhish — Phase 2.

Paper spec (Section III-C-2 and IV-C):
  - Model  : distilbert-base-uncased, DistilBertForSequenceClassification (2 labels)
  - Optimizer : AdamW, lr = 3e-4
  - Batch   : 32
  - Early stopping : patience = 3 on val-F1, max 10 epochs
  - Loss    : cross-entropy with class weights (handles SMS 13% phishing imbalance)
  - Adversarial : FGM (Fast Gradient Method) on word embeddings, ε = 0.25
  - Dataset  : SMS Spam Collection + SpamAssassin, split 70/10/20 (stratified)
  - Metrics  : accuracy, precision, recall, F1, ROC-AUC
  - MLflow   : all hyperparams + per-epoch metrics logged
  - Output  : api/models/distilbert_saved/ (best val-F1 checkpoint)

Usage:
    cd /path/to/IPD_InvisiPhish
    python -m training.train_distilbert
    python -m training.train_distilbert --lr 2e-5 --epochs 5 --batch_size 16
"""

import os
import sys
import argparse
import logging

import numpy as np
import torch
import torch.nn as nn
import mlflow
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import LinearLR
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
)
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.dataset_utils import build_combined_dataset  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "api", "models")
OUTPUT_DIR = os.path.join(MODELS_DIR, "distilbert_saved")

# ---------------------------------------------------------------------------
# Defaults (paper spec)
# ---------------------------------------------------------------------------
BASE_MODEL  = "distilbert-base-uncased"
MAX_LEN     = 256
LR          = 3e-4
BATCH_SIZE  = 32
MAX_EPOCHS  = 10
PATIENCE    = 3
FGM_EPS     = 0.25
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# PyTorch Dataset
# ---------------------------------------------------------------------------

class PhishingDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=MAX_LEN):
        self.encodings = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_len,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels":         self.labels[idx],
        }


# ---------------------------------------------------------------------------
# FGM — Fast Gradient Method adversarial training
# Paper spec Section III-C-2: "FGM-based adversarial training improves
# robustness to character-level obfuscation."
# ---------------------------------------------------------------------------

class FGM:
    """
    Perturbs the word embedding layer using the sign of the gradient.
    Call attack() after loss.backward(), then forward again for adv loss,
    then restore() before optimizer.step().
    """
    def __init__(self, model: nn.Module, epsilon: float = FGM_EPS,
                 emb_name: str = "word_embeddings"):
        self.model    = model
        self.epsilon  = epsilon
        self.emb_name = emb_name
        self._backup: dict = {}

    def attack(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad and self.emb_name in name and param.grad is not None:
                self._backup[name] = param.data.clone()
                norm = torch.norm(param.grad)
                if norm != 0 and not torch.isnan(norm):
                    param.data.add_(self.epsilon * param.grad / norm)

    def restore(self):
        for name, param in self.model.named_parameters():
            if name in self._backup:
                param.data = self._backup[name]
        self._backup.clear()


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------

@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader,
             device: torch.device, criterion: nn.Module) -> dict:
    model.eval()
    all_labels, all_preds, all_probs, total_loss = [], [], [], 0.0

    for batch in loader:
        input_ids      = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels         = batch["labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits  = outputs.logits
        loss    = criterion(logits, labels)
        total_loss += loss.item()

        probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
        preds = logits.argmax(dim=-1).cpu().numpy()

        all_labels.extend(labels.cpu().numpy())
        all_preds.extend(preds)
        all_probs.extend(probs)

    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    y_prob = np.array(all_probs)

    return {
        "loss":      total_loss / len(loader),
        "accuracy":  accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall":    recall_score(y_true, y_pred, zero_division=0),
        "f1":        f1_score(y_true, y_pred, zero_division=0),
        "roc_auc":   roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# Main training function
# ---------------------------------------------------------------------------

def train(
    lr:         float = LR,
    batch_size: int   = BATCH_SIZE,
    max_epochs: int   = MAX_EPOCHS,
    patience:   int   = PATIENCE,
    fgm_eps:    float = FGM_EPS,
    max_len:    int   = MAX_LEN,
):
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    device = torch.device("mps" if torch.backends.mps.is_available()
                          else "cuda" if torch.cuda.is_available()
                          else "cpu")
    logger.info(f"Device: {device}")

    # ------------------------------------------------------------------
    # 1. Load and split dataset (paper: 70/10/20 stratified)
    # ------------------------------------------------------------------
    df = build_combined_dataset()
    texts  = df["message"].tolist()
    labels = df["label"].tolist()

    X_train, X_tmp, y_train, y_tmp = train_test_split(
        texts, labels, test_size=0.30, stratify=labels, random_state=RANDOM_SEED
    )
    # Split the 30% remainder equally into val (10%) and test (20%)
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.667, stratify=y_tmp, random_state=RANDOM_SEED
    )
    logger.info(f"Split — train: {len(X_train)} | val: {len(X_val)} | test: {len(X_test)}")

    # ------------------------------------------------------------------
    # 2. Tokenizer + Datasets
    # ------------------------------------------------------------------
    tokenizer = DistilBertTokenizerFast.from_pretrained(BASE_MODEL)
    train_ds = PhishingDataset(X_train, y_train, tokenizer, max_len)
    val_ds   = PhishingDataset(X_val,   y_val,   tokenizer, max_len)
    test_ds  = PhishingDataset(X_test,  y_test,  tokenizer, max_len)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False, num_workers=0)

    # ------------------------------------------------------------------
    # 3. Class-weighted loss (handles phishing minority class)
    # ------------------------------------------------------------------
    n_phishing = sum(y_train)
    n_legit    = len(y_train) - n_phishing
    weight = torch.tensor(
        [1.0, n_legit / n_phishing], dtype=torch.float
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight)
    logger.info(f"Class weights — legit: 1.00 | phishing: {weight[1]:.2f}")

    # ------------------------------------------------------------------
    # 4. Model
    # ------------------------------------------------------------------
    model = DistilBertForSequenceClassification.from_pretrained(
        BASE_MODEL, num_labels=2
    ).to(device)

    # ------------------------------------------------------------------
    # 5. Optimizer + scheduler (paper: AdamW lr=3e-4, linear warmup)
    # ------------------------------------------------------------------
    total_steps   = len(train_loader) * max_epochs
    warmup_steps  = total_steps // 10
    optimizer     = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler     = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )
    fgm = FGM(model, epsilon=fgm_eps)

    # ------------------------------------------------------------------
    # 6. MLflow experiment
    # ------------------------------------------------------------------
    mlflow.set_experiment("InvisiPhish_DistilBERT")
    run = mlflow.start_run(run_name=f"distilbert_lr{lr}_bs{batch_size}")
    mlflow.log_params({
        "base_model":  BASE_MODEL,
        "lr":          lr,
        "batch_size":  batch_size,
        "max_epochs":  max_epochs,
        "patience":    patience,
        "fgm_eps":     fgm_eps,
        "max_len":     max_len,
        "train_size":  len(X_train),
        "val_size":    len(X_val),
        "test_size":   len(X_test),
        "n_phishing_train": n_phishing,
        "n_legit_train":    n_legit,
    })

    # ------------------------------------------------------------------
    # 7. Training loop with FGM adversarial training
    # ------------------------------------------------------------------
    best_val_f1    = 0.0
    patience_count = 0
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f" DistilBERT Fine-Tuning  |  lr={lr}  bs={batch_size}  FGM ε={fgm_eps}")
    print(f"{'='*60}\n")

    for epoch in range(1, max_epochs + 1):
        model.train()
        epoch_loss = 0.0

        for step, batch in enumerate(train_loader, 1):
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_batch   = batch["labels"].to(device)

            optimizer.zero_grad()

            # --- Normal forward + backward ---
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss    = criterion(outputs.logits, labels_batch)
            loss.backward()

            # --- FGM: perturb embeddings, forward + backward again ---
            fgm.attack()
            outputs_adv = model(input_ids=input_ids, attention_mask=attention_mask)
            loss_adv    = criterion(outputs_adv.logits, labels_batch)
            loss_adv.backward()
            fgm.restore()

            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            epoch_loss += loss.item()

            if step % 50 == 0:
                logger.info(
                    f"Epoch {epoch}/{max_epochs} | step {step}/{len(train_loader)} "
                    f"| loss {loss.item():.4f}"
                )

        avg_train_loss = epoch_loss / len(train_loader)

        # --- Validation ---
        val_metrics = evaluate(model, val_loader, device, criterion)

        logger.info(
            f"\nEpoch {epoch} — train_loss: {avg_train_loss:.4f} | "
            f"val_loss: {val_metrics['loss']:.4f} | "
            f"val_F1: {val_metrics['f1']:.4f} | "
            f"val_AUC: {val_metrics['roc_auc']:.4f}"
        )

        mlflow.log_metrics({
            "train_loss":    avg_train_loss,
            "val_loss":      val_metrics["loss"],
            "val_accuracy":  val_metrics["accuracy"],
            "val_precision": val_metrics["precision"],
            "val_recall":    val_metrics["recall"],
            "val_f1":        val_metrics["f1"],
            "val_roc_auc":   val_metrics["roc_auc"],
        }, step=epoch)

        # --- Early stopping (paper: patience=3 on val-F1) ---
        if val_metrics["f1"] > best_val_f1:
            best_val_f1    = val_metrics["f1"]
            patience_count = 0
            model.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)
            logger.info(f"  ✓ New best val-F1: {best_val_f1:.4f} — checkpoint saved")
        else:
            patience_count += 1
            logger.info(
                f"  No improvement ({patience_count}/{patience}). "
                f"Best val-F1 so far: {best_val_f1:.4f}"
            )
            if patience_count >= patience:
                logger.info(f"Early stopping triggered at epoch {epoch}.")
                break

    # ------------------------------------------------------------------
    # 8. Final test-set evaluation on best checkpoint
    # ------------------------------------------------------------------
    logger.info("\nLoading best checkpoint for test evaluation…")
    best_model = DistilBertForSequenceClassification.from_pretrained(OUTPUT_DIR).to(device)
    test_metrics = evaluate(best_model, test_loader, device, criterion)

    # Confusion matrix
    best_model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in test_loader:
            out = best_model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            )
            all_preds.extend(out.logits.argmax(dim=-1).cpu().numpy())
            all_labels.extend(batch["labels"].numpy())
    cm = confusion_matrix(all_labels, all_preds)

    print(f"\n{'='*60}")
    print(f" TEST SET RESULTS")
    print(f"{'='*60}")
    print(f"  Accuracy  : {test_metrics['accuracy']:.4f}")
    print(f"  Precision : {test_metrics['precision']:.4f}")
    print(f"  Recall    : {test_metrics['recall']:.4f}")
    print(f"  F1        : {test_metrics['f1']:.4f}")
    print(f"  ROC-AUC   : {test_metrics['roc_auc']:.4f}")
    print(f"  Confusion matrix:\n{cm}")
    print(f"{'='*60}\n")

    mlflow.log_metrics({
        "test_accuracy":  test_metrics["accuracy"],
        "test_precision": test_metrics["precision"],
        "test_recall":    test_metrics["recall"],
        "test_f1":        test_metrics["f1"],
        "test_roc_auc":   test_metrics["roc_auc"],
        "best_val_f1":    best_val_f1,
    })
    mlflow.log_artifact(OUTPUT_DIR)
    mlflow.end_run()

    logger.info(f"Training complete. Model saved → {OUTPUT_DIR}")
    return test_metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fine-tune DistilBERT for phishing detection (InvisiPhish Phase 2)"
    )
    parser.add_argument("--lr",         type=float, default=LR,         help=f"Learning rate (default: {LR})")
    parser.add_argument("--batch_size", type=int,   default=BATCH_SIZE, help=f"Batch size (default: {BATCH_SIZE})")
    parser.add_argument("--epochs",     type=int,   default=MAX_EPOCHS, help=f"Max epochs (default: {MAX_EPOCHS})")
    parser.add_argument("--patience",   type=int,   default=PATIENCE,   help=f"Early stopping patience (default: {PATIENCE})")
    parser.add_argument("--fgm_eps",    type=float, default=FGM_EPS,    help=f"FGM epsilon (default: {FGM_EPS})")
    args = parser.parse_args()

    train(
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        patience=args.patience,
        fgm_eps=args.fgm_eps,
    )
