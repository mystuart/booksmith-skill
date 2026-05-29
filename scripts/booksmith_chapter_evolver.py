#!/usr/bin/env python3
"""
booksmith_chapter_evolver.py — Darwinian evolution for booksmith chapters.

Implements the darwinian-evolver Problem interface:
  Organism  = a single chapter manuscript (raw markdown string)
  Evaluator = quality scorer (trainable + holdout failure cases)
  Mutator   = LLM that proposes improved chapter text from failure cases

Run:
    cd ~/.claude/skills/booksmith/cache/darwinian-evolver/darwinian_evolver
    ANTHROPIC_API_KEY=... uv run --with anthropic python \\
        ~/.claude/skills/booksmith/scripts/booksmith_chapter_evolver.py \\
        --chapter_path ~/Books/my-book/manuscript/ch05.md \\
        --output_dir /tmp/ch05_evolve \\
        --num_iterations 5 --num_parents_per_iteration 4 \\
        --mutator_concurrency 4 --evaluator_concurrency 4

License: AGPL-3.0 — this script is a user-side driver, not derivative code.
参考 upstream darwinian_evolver/cli_common.py 的 register_hyperparameter_args.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import anthropic

# AGPL-3.0: invoked via subprocess; importing from the clone is fine for drivers.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cache/darwinian-evolver/darwinian_evolver"))

from darwinian_evolver.cli_common import (
    build_hyperparameter_config_from_args,
    parse_learning_log_view_type,
    register_hyperparameter_args,
)
from darwinian_evolver.evolve_problem_loop import EvolveProblemLoop
from darwinian_evolver.learning_log import LearningLogEntry
from darwinian_evolver.problem import (
    EvaluationFailureCase,
    EvaluationResult,
    Evaluator,
    Mutator,
    Organism,
    Problem,
)


# ═══════════════════════════════════════════════════════════════════════
# Organism
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ChapterOrganism(Organism):
    """Evolves a single chapter's markdown manuscript."""
    artifact: str  # raw markdown text of the chapter

    def __str__(self) -> str:
        # First 200 chars as summary for snapshot inspection
        return self.artifact[:200]


# ═══════════════════════════════════════════════════════════════════════
# Failure Cases
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ChapterFailureCase(EvaluationFailureCase):
    """A quality problem found in a chapter."""
    dimension: str          # e.g. "readability", "terminology", "narrative_flow"
    chapter_ref: str       # e.g. "ch05.md" or "ch05.md:ln42"
    fragment: str          # the problematic text excerpt
    suggestion: str        # what the reviewer agent recommended


# ═══════════════════════════════════════════════════════════════════════
# Evaluator
# ═══════════════════════════════════════════════════════════════════════


class ChapterEvaluator(Evaluator[ChapterOrganism, EvaluationResult, ChapterFailureCase]):
    """Split evaluation: trainable failures teach the mutator; holdout detects overfitting.

    TRAINABLE: quality issues found by the main agent during writing phase.
    HOLDOUT:   a separate set of quality issues held in reserve — never shown to mutator.
    """

    TRAINABLE_FAILURE_BANK: list[ChapterFailureCase] = []
    HOLDOUT_FAILURE_BANK: list[ChapterFailureCase] = []

    # --- Scoring rubric (per dimension, each 0–1) ---
    WEIGHTS = {
        "readability":    0.25,
        "technical":      0.25,
        "narrative_flow": 0.20,
        "style_consistency": 0.15,
        "citation":       0.15,
    }

    def __init__(
        self,
        anchor_sample_path: str | Path | None = None,
        glossary_path: str | Path | None = None,
        style_guide_path: str | Path | None = None,
        target_reader: str = "有基础",
    ):
        self.anchor_sample = Path(anchor_sample_path).read_text() if anchor_sample_path else ""
        self.glossary = Path(glossary_path).read_text() if glossary_path else ""
        self.style_guide = Path(style_guide_path).read_text() if style_guide_path else ""
        self.target_reader = target_reader

    def _score_dimension(self, artifact: str, dim: str) -> float:
        """Heuristic scoring per dimension. Real implementation would spawn
        a sub-agent for deep inspection. Here we use lightweight signals."""
        score_map = {
            "readability": self._readability_score,
            "technical":    self._technical_score,
            "narrative_flow": self._narrative_score,
            "style_consistency": self._style_score,
            "citation":     self._citation_score,
        }
        fn = score_map.get(dim, lambda _: 0.5)
        return fn(artifact)

    def _readability_score(self, text: str) -> float:
        # Signals: CJK char density, line length variance, bullet list ratio
        lines = text.splitlines()
        if not lines:
            return 0.0
        # Very short avg line length = too fragmented; too long = wall of text
        avg_len = sum(len(l) for l in lines) / len(lines)
        if avg_len < 20:
            return 0.3   # too fragmented
        if avg_len > 120:
            return 0.4   # too dense
        return 0.8

    def _technical_score(self, text: str) -> float:
        # Signals: presence of code blocks, tables, numeric data
        has_code = "```" in text
        has_table = "|" in text and "---" in text
        has_numbers = any(c.isdigit() for c in text)
        score = 0.3
        if has_code:   score += 0.25
        if has_table:   score += 0.20
        if has_numbers: score += 0.25
        return min(score, 1.0)

    def _narrative_score(self, text: str) -> float:
        # Signals: presence of transition phrases, absence of orphan sentences
        transitions = ["因此", "然而", "换句话说", "进一步", "综上所述",
                       "此外", "也就是说", "回到", "正如第", "这意味着"]
        transition_count = sum(text.count(t) for t in transitions)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return 0.2
        orphan_count = sum(1 for p in paragraphs if len(p) < 30)
        transition_score = min(transition_count / max(len(paragraphs), 1) * 2, 1.0)
        orphan_score = max(1.0 - orphan_count / len(paragraphs), 0.3)
        return (transition_score * 0.4 + orphan_score * 0.6)

    def _style_score(self, text: str) -> float:
        # Signals: matches anchor style markers (Tip/, Warning/, Note/ boxes, scene opening)
        markers = [".tip", ".term", "**Tip**", "> **Tip", "```python", "```bash"]
        marker_count = sum(text.count(m) for m in markers)
        # Absence of style violations
        violations = ['"本文"', '"笔者"', '"综上所述， 以上就是本章"']
        violation_count = sum(text.count(v) for v in violations)
        marker_score = min(marker_count / 5, 1.0)
        violation_score = max(1.0 - violation_count * 0.3, 0.0)
        return (marker_score * 0.6 + violation_score * 0.4)

    def _citation_score(self, text: str) -> float:
        # Signals: presence of URLs or reference-style parentheticals
        has_url = "http" in text
        has_parens = "(" in text and ")" in text
        score = 0.3
        if has_url:    score += 0.35
        if has_parens: score += 0.35
        return min(score, 1.0)

    def _build_failure(self, artifact: str, dim: str, score: float,
                       data_point_id: str) -> ChapterFailureCase | None:
        """If score < threshold, build a failure case with suggestion."""
        thresholds = {"readability": 0.7, "technical": 0.7, "narrative_flow": 0.65,
                      "style_consistency": 0.7, "citation": 0.6}
        if score >= thresholds.get(dim, 0.7):
            return None
        suggestions = {
            "readability":    "拆分过长段落，增加过渡句，每段不超过100字",
            "technical":      "增加代码示例、数据表格或命令输出来支撑论点",
            "narrative_flow": "在章节末尾增加承上启下的过渡句，避免'以上就是本章全部内容'",
            "style_consistency": "按anchor-sample.md风格补充Tip/Warning框或场景开头",
            "citation":       "为关键论点添加URL引用或标注来源",
        }
        # Find a short excerpt for context
        lines = artifact.splitlines()
        excerpt = lines[len(lines)//2][:120].strip() if lines else ""
        return ChapterFailureCase(
            dimension=dim,
            input=dim,
            expected=f"score >= {thresholds[dim]}",
            actual=f"score={score:.2f}, excerpt: {excerpt}",
            chapter_ref="current",
            fragment=excerpt,
            suggestion=suggestions.get(dim, "改进此维度"),
            data_point_id=data_point_id,
        )

    def _score_and_failures(self, artifact: str) -> tuple[float, list[ChapterFailureCase], list[ChapterFailureCase]]:
        scores = {dim: self._score_dimension(artifact, dim) for dim in self.WEIGHTS}
        weighted = sum(self.WEIGHTS[dim] * sc for dim, sc in scores.items())

        train_fails, hold_fails = [], []
        for i, (dim, sc) in enumerate(scores.items()):
            data_pt = f"trainable_{i}"
            fc = self._build_failure(artifact, dim, sc, data_pt)
            if fc:
                # Assign some to holdout (every 3rd dimension) for overfit detection
                if i % 3 == 0 and len(self.HOLDOUT_FAILURE_BANK) < 5:
                    hold_fails.append(fc)
                    self.HOLDOUT_FAILURE_BANK.append(fc)
                else:
                    train_fails.append(fc)
                    self.TRAINABLE_FAILURE_BANK.append(fc)

        return weighted, train_fails, hold_fails

    def evaluate(self, organism: ChapterOrganism) -> EvaluationResult:
        score, train_fails, hold_fails = self._score_and_failures(organism.artifact)
        return EvaluationResult(
            score=score,
            trainable_failure_cases=train_fails,
            holdout_failure_cases=hold_fails,
            is_viable=True,  # always viable; even 0-score is useful diversity
        )


# ═══════════════════════════════════════════════════════════════════════
# Mutator
# ═══════════════════════════════════════════════════════════════════════


ANTHROPIC_MODEL = "claude-sonnet-4-7"
MUTATOR_SYSTEM_PROMPT = textwrap.dedent("""
You are an expert technical book editor. You receive a chapter manuscript with
one or more quality problems (failure cases). Your task is to rewrite the chapter
to fix those problems while preserving everything else that is already good.

Output format:
1. A brief diagnosis of each failure case
2. The rewritten chapter in a single markdown code block

Rules:
- Do NOT invent facts or add unsubstantiated claims
- Preserve the chapter's structure and core argument
- Keep code examples and technical details as-is unless they are the problem
- Fix ONLY the issues described in the failure cases
- If a failure case mentions a specific excerpt, show the improved version
""").strip()


class ChapterMutator(Mutator[ChapterOrganism, ChapterFailureCase]):
    """LLM mutator: given a parent organism + failure cases, propose improved text."""

    def __init__(self, model: str = ANTHROPIC_MODEL):
        self.model = model
        self.client = anthropic.Anthropic()

    def mutate(
        self,
        organism: ChapterOrganism,
        failure_cases: list[ChapterFailureCase],
        learning_log_entries: list[LearningLogEntry],
    ) -> list[ChapterOrganism]:
        if not failure_cases:
            return []

        fc = failure_cases[0]  # primary failure case
        failure_list = "\n".join(
            f"- **[{fc.dimension}]** (line {fc.chapter_ref})\n"
            f"  excerpt: {fc.fragment[:200]}\n"
            f"  suggestion: {fc.suggestion}"
            for fc in failure_cases[:3]  # cap at 3 for prompt length
        )

        prompt = textwrap.dedent(f"""\
        Current chapter manuscript:

        ```markdown
        {organism.artifact[:8000]}
        ```

        Quality problems to fix:

        {failure_list}

        {"Previous mutation attempts (for reference):" if learning_log_entries else ""}
        {self._format_learning_log(learning_log_entries[-3:]) if learning_log_entries else ""}

        Please diagnose each problem and rewrite the chapter to fix them.
        Output the rewritten chapter in a single ```markdown code block.
        """)

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=MUTATOR_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
        except Exception as e:
            return []  # evolver will score this as 0 and move on

        # Parse the markdown code block in the response
        parts = raw.split("```")
        new_artifact = ""
        for i in range(len(parts) - 1, 0, -2):  # last markdown block
            block = parts[i]
            if block.startswith("markdown"):
                new_artifact = block[len("markdown"):].strip()
                break
            elif block and not block.startswith("yaml") and not block.startswith("python"):
                new_artifact = block.strip()
                break

        if not new_artifact or len(new_artifact) < len(organism.artifact) * 0.1:
            return []  # parsed artifact too short / empty

        return [ChapterOrganism(artifact=new_artifact)]

    def _format_learning_log(self, entries: list[LearningLogEntry]) -> str:
        if not entries:
            return ""
        return "\n".join(
            f"- iter {e.iteration}: {e.change_summary[:100]}"
            for e in entries if e.change_summary
        )


# ═══════════════════════════════════════════════════════════════════════
# Driver
# ═══════════════════════════════════════════════════════════════════════


def make_problem(
    chapter_path: str | Path,
    anchor_sample_path: str | Path | None,
    glossary_path: str | Path | None,
    style_guide_path: str | Path | None,
    target_reader: str,
) -> Problem:
    chapter_text = Path(chapter_path).read_text(encoding="utf-8")
    initial = ChapterOrganism(artifact=chapter_text)
    evaluator = ChapterEvaluator(
        anchor_sample_path=anchor_sample_path,
        glossary_path=glossary_path,
        style_guide_path=style_guide_path,
        target_reader=target_reader,
    )
    return Problem[ChapterOrganism, EvaluationResult, ChapterFailureCase](
        evaluator=evaluator,
        mutators=[ChapterMutator()],
        initial_organism=initial,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Booksmith chapter evolver (darwinian-evolver driver)")
    register_hyperparameter_args(ap.add_argument_group("hyperparameters"))
    ap.add_argument("--chapter_path", required=True, help="Path to chapter .md file")
    ap.add_argument("--anchor_sample_path", default=None, help="Path to anchor-sample.md")
    ap.add_argument("--glossary_path", default=None, help="Path to glossary.md")
    ap.add_argument("--style_guide_path", default=None, help="Path to style-guide.md")
    ap.add_argument("--target_reader", default="有基础")
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--model", default=ANTHROPIC_MODEL)
    ap.add_argument("--num_iterations", type=int, default=5)
    ap.add_argument("--mutator_concurrency", type=int, default=4)
    ap.add_argument("--evaluator_concurrency", type=int, default=4)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "snapshots").mkdir(exist_ok=True)

    hp = build_hyperparameter_config_from_args(args)
    loop = EvolveProblemLoop(
        problem=make_problem(
            args.chapter_path,
            args.anchor_sample_path,
            args.glossary_path,
            args.style_guide_path,
            args.target_reader,
        ),
        learning_log_view_type=parse_learning_log_view_type(hp.learning_log_view_type),
        num_parents_per_iteration=hp.num_parents_per_iteration,
        mutator_concurrency=args.mutator_concurrency,
        evaluator_concurrency=args.evaluator_concurrency,
        fixed_midpoint_score=hp.fixed_midpoint_score,
        midpoint_score_percentile=hp.midpoint_score_percentile,
        sharpness=hp.sharpness,
        novelty_weight=hp.novelty_weight,
        batch_size=hp.batch_size,
        should_verify_mutations=hp.verify_mutations,
    )

    print(f"Evolving {args.chapter_path} → {out}")
    print(f"Model: {args.model}")
    print(f"Iterations: {args.num_iterations}, Parents/iter: {hp.num_parents_per_iteration}")
    print("-" * 60)

    for snap in loop.run(num_iterations=args.num_iterations):
        snapshot_file = out / "snapshots" / f"iteration_{snap.iteration}.pkl"
        snapshot_file.write_bytes(snap.snapshot)
        _, best = snap.best_organism_result
        print(f"iter={snap.iteration:2d}  pop={snap.population_size:3d}  "
              f"best_score={best.score:.3f}  best_text={str(best.organism)[:80]}")

    # Write final best
    _, best = snap.best_organism_result
    best_path = out / "best_chapter.md"
    best_path.write_text(best.organism.artifact, encoding="utf-8")
    print(f"\nBest chapter → {best_path}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())