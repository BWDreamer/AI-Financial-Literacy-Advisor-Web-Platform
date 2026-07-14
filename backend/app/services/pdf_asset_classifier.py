from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
import json
import math
from typing import Any


@dataclass(frozen=True)
class AssetCategoryDefinition:
    name: str
    semantic_definition: str


ASSET_CATEGORY_DEFINITIONS = (
    AssetCategoryDefinition(
        name="cash",
        semantic_definition=(
            "Cash, savings, bank balances, deposits, or money received "
            "and held in a cash-like form."
        ),
    ),
    AssetCategoryDefinition(
        name="stocks",
        semantic_definition=(
            "Shares, equities, stock holdings, or equity investment value."
        ),
    ),
    AssetCategoryDefinition(
        name="bonds",
        semantic_definition=(
            "Government or corporate bonds and other fixed-income "
            "securities."
        ),
    ),
    AssetCategoryDefinition(
        name="property",
        semantic_definition=(
            "Residential, commercial, or investment real estate and land."
        ),
    ),
    AssetCategoryDefinition(
        name="vehicle",
        semantic_definition=(
            "Cars, motorcycles, boats, and other owned vehicles."
        ),
    ),
    AssetCategoryDefinition(
        name="others",
        semantic_definition=(
            "Owned assets with monetary value that do not fit another "
            "allowed category."
        ),
    ),
)

ASSET_TYPES = tuple(
    definition.name
    for definition in ASSET_CATEGORY_DEFINITIONS
)
NOT_ASSET = "not_asset"
ALLOWED_ASSET_CLASSIFICATIONS = ASSET_TYPES + (NOT_ASSET,)
MIN_ASSET_CLASSIFICATION_CONFIDENCE = 0.55

ASSET_CLASSIFICATION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {
                        "type": "string",
                    },
                    "classification": {
                        "type": "string",
                        "enum": list(ALLOWED_ASSET_CLASSIFICATIONS),
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": [
                    "candidate_id",
                    "classification",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["classifications"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class AssetCandidate:
    candidate_id: str
    description: str
    amount: Decimal
    source_line: str


@dataclass(frozen=True)
class AssetClassification:
    candidate_id: str
    classification: str
    confidence: float


@dataclass(frozen=True)
class ExtractedAsset:
    asset_type: str
    amount: Decimal
    source_line: str


AssetClassifier = Callable[
    [list[AssetCandidate]],
    Awaitable[list[AssetClassification]],
]


def build_asset_classification_prompt(
    candidates: list[AssetCandidate],
) -> str:
    category_lines = [
        f"- {definition.name}: {definition.semantic_definition}"
        for definition in ASSET_CATEGORY_DEFINITIONS
    ]
    rows = [
        {
            "candidate_id": candidate.candidate_id,
            "description": candidate.description,
            "source_line": candidate.source_line,
            "amount_from_backend": f"{candidate.amount:.2f}",
        }
        for candidate in candidates
    ]

    return "\n".join(
        [
            (
                "Classify monetary items from a financial PDF into "
                "asset categories."
            ),
            (
                "The backend has already parsed every amount using commas "
                "as thousands separators and a period as the decimal point."
            ),
            (
                "Treat amount_from_backend as authoritative. Do not infer, "
                "recalculate, add, remove, split, or rewrite amounts."
            ),
            (
                "Classify an item as an asset when it represents value owned "
                "or received by the user, or the acquisition or stated value "
                "of a durable or investment asset."
            ),
            (
                "For an acquisition of a durable or investment asset, "
                "classify the acquired asset rather than the payment method."
            ),
            (
                "Routine consumption, service payments, fees, liabilities, "
                "repayments, and amounts that do not establish owned value "
                "must be not_asset."
            ),
            (
                "For bank transaction tables, money received and retained "
                "may be cash; outgoing everyday payments are not assets."
            ),
            "Use only these classification semantics:",
            *category_lines,
            (
                f"- {NOT_ASSET}: The monetary item is not an asset value "
                "under the rules above, or its meaning is too uncertain."
            ),
            (
                "Return exactly one classification for every candidate, "
                "matching the supplied JSON Schema. Do not answer the user."
            ),
            "Monetary items:",
            json.dumps(rows),
        ]
    )


def normalize_asset_classification_payload(
    payload: dict[str, Any],
    candidates: list[AssetCandidate],
) -> list[AssetClassification]:
    candidate_ids = {
        candidate.candidate_id
        for candidate in candidates
    }
    rows = payload.get("classifications")
    if not isinstance(rows, list):
        return []

    classifications: list[AssetClassification] = []
    seen_ids: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id not in candidate_ids or candidate_id in seen_ids:
            continue

        classification = (
            str(row.get("classification") or NOT_ASSET)
            .strip()
            .lower()
        )
        if classification not in ALLOWED_ASSET_CLASSIFICATIONS:
            classification = NOT_ASSET

        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0
        if not math.isfinite(confidence):
            confidence = 0.0

        classifications.append(
            AssetClassification(
                candidate_id=candidate_id,
                classification=classification,
                confidence=max(0.0, min(confidence, 1.0)),
            )
        )
        seen_ids.add(candidate_id)

    return classifications


def select_classified_assets(
    candidates: list[AssetCandidate],
    classifications: list[AssetClassification],
) -> list[ExtractedAsset]:
    classifications_by_id = {
        classification.candidate_id: classification
        for classification in classifications
    }
    assets: list[ExtractedAsset] = []

    for candidate in candidates:
        classification = classifications_by_id.get(candidate.candidate_id)
        if classification is None:
            continue
        if (
            classification.confidence
            < MIN_ASSET_CLASSIFICATION_CONFIDENCE
        ):
            continue
        if classification.classification not in ASSET_TYPES:
            continue

        assets.append(
            ExtractedAsset(
                asset_type=classification.classification,
                amount=candidate.amount,
                source_line=candidate.source_line,
            )
        )

    return assets
