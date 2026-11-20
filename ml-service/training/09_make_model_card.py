"""Re-generate reports/MODEL_CARD.md from metrics.json (stage 8 also embeds it in the bundle)."""
from training import model_card
from training.common import log, parse


def main() -> None:
    ctx = parse("Model card")
    out = ctx.reports / "MODEL_CARD.md"
    out.write_text(model_card.build(ctx), encoding="utf-8")
    log.info("wrote %s", out)


if __name__ == "__main__":
    main()
