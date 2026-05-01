from __future__ import annotations

import json
import inspect
import os
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Sequence
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid4, uuid5

from langsmith import schemas
from langsmith.evaluation import aevaluate
from langsmith.run_helpers import tracing_context

from packages.agents.langsmith_utils import (
    get_langsmith_client,
    get_langsmith_project,
    should_upload_eval_results,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "evals" / "fixtures"
RESULTS_DIR = ROOT_DIR / "evals" / "results"

_LANGSMITH_ENV_KEYS = (
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_API_KEY",
)


def load_json_fixture(name: str) -> list[dict[str, Any]]:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text())


def build_examples(eval_id: str, cases: Iterable[dict[str, Any]]) -> list[schemas.Example]:
    dataset_id = uuid4()
    created_at = datetime.now(timezone.utc)
    examples: list[schemas.Example] = []
    for case in cases:
        examples.append(
            schemas.Example(
                id=uuid5(NAMESPACE_URL, f"{eval_id}:{case['id']}"),
                dataset_id=dataset_id,
                inputs=case["inputs"],
                outputs=case["expected"],
                metadata={
                    "eval_id": eval_id,
                    "case_id": case["id"],
                    "category": case["category"],
                },
                created_at=created_at,
            )
        )
    return examples


@contextmanager
def _local_eval_env(upload_results: bool):
    if upload_results:
        yield
        return

    original: dict[str, str | None] = {key: os.environ.get(key) for key in _LANGSMITH_ENV_KEYS}
    try:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        os.environ.pop("LANGSMITH_API_KEY", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def ensure_remote_dataset(
    *,
    client: Any,
    eval_id: str,
    cases: Sequence[dict[str, Any]],
    description: str,
) -> Any:
    dataset_name = f"{get_langsmith_project()}-{eval_id.lower()}-dataset"
    existing = next(client.list_datasets(dataset_name=dataset_name, limit=1), None)
    dataset = existing or client.create_dataset(dataset_name=dataset_name, description=description)
    examples = []
    for case in cases:
        examples.append(
            {
                "id": str(uuid5(NAMESPACE_URL, f"{eval_id}:{case['id']}")),
                "inputs": case["inputs"],
                "outputs": case["expected"],
                "metadata": {
                    "eval_id": eval_id,
                    "case_id": case["id"],
                    "category": case["category"],
                },
            }
        )
    client.create_examples(dataset_id=dataset.id, examples=examples)
    return dataset


async def run_async_eval(
    *,
    eval_id: str,
    cases: Sequence[dict[str, Any]],
    target: Any,
    evaluators: Sequence[Any],
    threshold: float,
    description: str,
) -> tuple[dict[str, Any], Path]:
    upload_results = should_upload_eval_results()
    client = get_langsmith_client() if upload_results else None
    project_name = get_langsmith_project("evals")
    examples = build_examples(eval_id, cases)
    data: Any = examples
    if upload_results and client is not None:
        dataset = ensure_remote_dataset(
            client=client,
            eval_id=eval_id,
            cases=cases,
            description=description,
        )
        data = dataset.id

    with _local_eval_env(upload_results):
        if upload_results:
            with tracing_context(
                enabled=True,
                client=client,
                project_name=project_name,
                tags=["pair-cooking", "eval", eval_id],
                metadata={"eval_id": eval_id, "case_count": len(cases)},
            ):
                experiment = await aevaluate(
                    target,
                    data=data,
                    evaluators=evaluators,
                    client=client,
                    upload_results=True,
                    experiment_prefix=eval_id,
                    description=description,
                    metadata={"eval_id": eval_id, "case_count": len(cases)},
                )
                await experiment.wait()
                rows = [row async for row in experiment]
        else:
            rows = await _run_local_eval(
                examples=examples,
                target=target,
                evaluators=evaluators,
            )

    summary = summarize_rows(eval_id=eval_id, threshold=threshold, rows=rows)
    result_path = write_result_file(
        eval_id=eval_id,
        payload={
            "eval_id": eval_id,
            "description": description,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "threshold": threshold,
            "summary": summary,
            "rows": [serialize_row(row) for row in rows],
        },
    )
    return summary, result_path


def summarize_rows(
    *,
    eval_id: str,
    threshold: float,
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    awarded = 0.0
    available = 0.0
    case_details: list[dict[str, Any]] = []

    for row in rows:
        serialized = serialize_evaluation_results(row.get("evaluation_results", {}))
        row_awarded = 0.0
        row_available = 0.0
        for result in serialized:
            score = float(result.get("score") or 0)
            value = result.get("value")
            available_points = 1.0
            if isinstance(value, dict) and "available" in value:
                available_points = float(value["available"])
            row_awarded += score
            row_available += available_points

        awarded += row_awarded
        available += row_available
        case_details.append(
            {
                "case_id": row["example"].metadata.get("case_id"),
                "category": row["example"].metadata.get("category"),
                "awarded": row_awarded,
                "available": row_available,
            }
        )

    ratio = (awarded / available) if available else 0.0
    return {
        "eval_id": eval_id,
        "awarded": awarded,
        "available": available,
        "ratio": ratio,
        "threshold": threshold,
        "passed": ratio >= threshold,
        "case_count": len(rows),
        "cases": case_details,
    }


async def _run_local_eval(
    *,
    examples: Sequence[schemas.Example],
    target: Any,
    evaluators: Sequence[Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        outputs = target(example.inputs)
        if inspect.isawaitable(outputs):
            outputs = await outputs
        run = SimpleNamespace(outputs=outputs)
        results = []
        for evaluator in evaluators:
            evaluation = evaluator(run, example)
            if inspect.isawaitable(evaluation):
                evaluation = await evaluation
            results.append(SimpleNamespace(**evaluation))
        rows.append(
            {
                "run": run,
                "example": example,
                "evaluation_results": {"results": results},
            }
        )
    return rows


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row["example"].metadata.get("case_id"),
        "category": row["example"].metadata.get("category"),
        "inputs": row["example"].inputs,
        "expected": row["example"].outputs,
        "outputs": row["run"].outputs,
        "evaluations": serialize_evaluation_results(row.get("evaluation_results", {})),
    }


def serialize_evaluation_results(payload: Any) -> list[dict[str, Any]]:
    raw_results = payload.get("results", []) if isinstance(payload, dict) else []
    serialized: list[dict[str, Any]] = []
    for result in raw_results:
        serialized.append(
            {
                "key": getattr(result, "key", None),
                "score": getattr(result, "score", None),
                "value": getattr(result, "value", None),
                "comment": getattr(result, "comment", None),
            }
        )
    return serialized


def write_result_file(*, eval_id: str, payload: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"{eval_id}-{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path
