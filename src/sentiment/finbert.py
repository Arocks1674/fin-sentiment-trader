"""FinBERT sentiment scoring.

Model: ProsusAI/finbert, BERT fine-tuned on financial text (Financial
PhraseBank). It outputs three probabilities: positive, negative, neutral.

We score "title. description" because headlines alone are often too short
to carry tone, and the description adds context without the full article's
length (FinBERT truncates at 512 tokens).
"""
from dataclasses import dataclass

MODEL_NAME = "ProsusAI/finbert"


def article_text(title: str, description: str | None) -> str:
    title = (title or "").strip()
    desc = (description or "").strip()
    if desc and desc.lower() != title.lower():
        return f"{title}. {desc}"
    return title


@dataclass
class FinBertScorer:
    model_name: str = MODEL_NAME
    batch_size: int = 16
    device: str = "cpu"

    def __post_init__(self):
        # Imported here so the rest of the project (and its tests) run without torch.
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device)
        self.model.eval()
        # Read label order from the model config instead of hard-coding it.
        self.labels = [self.model.config.id2label[i].lower() for i in range(self.model.config.num_labels)]
        missing = {"positive", "negative", "neutral"} - set(self.labels)
        if missing:
            raise ValueError(f"{self.model_name} labels {self.labels} lack {missing}")

    def score(self, texts: list[str]) -> list[dict]:
        """Return one dict per text: positive, negative, neutral, label, score."""
        out = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            enc = self.tokenizer(batch, padding=True, truncation=True, max_length=512,
                                 return_tensors="pt").to(self.device)
            with self._torch.no_grad():
                probs = self._torch.softmax(self.model(**enc).logits, dim=-1).cpu().tolist()
            for p in probs:
                d = dict(zip(self.labels, p))
                out.append(to_record(d["positive"], d["negative"], d["neutral"]))
        return out


def to_record(pos: float, neg: float, neu: float) -> dict:
    probs = {"positive": pos, "negative": neg, "neutral": neu}
    return {**probs, "label": max(probs, key=probs.get), "score": pos - neg}
