from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db import transaction
from django.utils import timezone

from timb_dashboard.models import TobaccoGrade
from .models import (
    AggregatedGrade,
    AggregatedGradeComponent,
    AggregationRuleSet,
    ClientOrder,
    MerchantInventory,
)


# Heuristic nicotine estimates by category (kg/kg basis, percent nicotine)
NICOTINE_BY_CATEGORY = {
    "PRIMING": (1.0, 2.0),
    "LUG": (2.0, 3.0),
    "LEAF": (2.5, 3.5),
    "TIP": (1.5, 2.5),
    "STRIP": (3.0, 4.5),
    "CUTTER": (2.0, 3.0),
    "SMOKING": (1.0, 2.0),
    "SCRAP": (0.5, 1.0),
}


def _get_inventory_map(merchant) -> Dict[int, Decimal]:
    """Return {grade_id: available_quantity_kg} for merchant inventory."""
    inv_map: Dict[int, Decimal] = {}
    for item in MerchantInventory.objects.filter(merchant=merchant):
        inv_map[item.grade_id] = inv_map.get(item.grade_id, Decimal("0")) + item.available_quantity
    return inv_map


def _estimate_nicotine_from_components(components: List[Tuple[TobaccoGrade, Decimal]]) -> Tuple[float, float]:
    """Weighted estimate of nicotine range based on category heuristics."""
    if not components:
        return (0.0, 0.0)
    min_total = 0.0
    max_total = 0.0
    for grade, pct in components:
        cat = grade.category
        low, high = NICOTINE_BY_CATEGORY.get(cat, (1.0, 2.5))
        weight = float(pct) / 100.0
        min_total += low * weight
        max_total += high * weight
    return (round(min_total, 2), round(max_total, 2))


def _compute_achievable_kg(components: List[Tuple[TobaccoGrade, Decimal]], inv_map: Dict[int, Decimal]) -> Tuple[Decimal, Dict[int, Decimal]]:
    """Compute achievable total kg using current inventory and per-component kg breakdown.

    For a target blend where each component is percentage p_i, the limiting factor is:
        min_i available_i / (p_i/100)
    """
    if not components:
        return Decimal("0"), {}
    limits: List[Decimal] = []
    for grade, pct in components:
        available = inv_map.get(grade.id, Decimal("0"))
        denom = Decimal(pct) / Decimal("100") if Decimal(pct) > 0 else Decimal("1")
        if denom > 0:
            limits.append((available / denom).quantize(Decimal("0.01")))
    total_kg = min(limits) if limits else Decimal("0")
    per_comp_kg: Dict[int, Decimal] = {}
    for grade, pct in components:
        kg = (total_kg * (Decimal(pct) / Decimal("100"))).quantize(Decimal("0.01"))
        per_comp_kg[grade.id] = kg
    return total_kg, per_comp_kg


def _pick_top_grades_by_category(category: str, limit: int = 3, exclude_ids: List[int] | None = None) -> List[TobaccoGrade]:
    exclude_ids = exclude_ids or []
    return list(
        TobaccoGrade.objects.filter(category=category, is_active=True, is_tradeable=True)
        .exclude(id__in=exclude_ids)
        .order_by("quality_level", "-base_price")[:limit]
    )


@transaction.atomic
def run_rule_set(rule_set: AggregationRuleSet):
    """Run an aggregation rule set and persist AggregatedGrade outputs.

    Produces outputs per the user's requirements:
      - For AI_TREND and AI_SPEC: derive possible grades from all TIMB grades, then compute achievable blends based on inventory
      - For USER_RULE: operate strictly on inventory-defined composition
      - For AI_CLIENT_DEMAND: derive possibilities from all grades and then compute achievable blends matching demand
    """
    merchant = rule_set.merchant
    inv_map = _get_inventory_map(merchant)

    outputs: List[AggregatedGrade] = []

    def create_output(name: str, components: List[Tuple[TobaccoGrade, Decimal]], label: str = ""):
        nicotine_range = _estimate_nicotine_from_components(components)
        total_kg, per_comp_kg = _compute_achievable_kg(components, inv_map)

        agg = AggregatedGrade.objects.create(
            merchant=merchant,
            rule_set=rule_set,
            name=name,
            label=label,
            characteristics={
                "estimated_nicotine_min": nicotine_range[0],
                "estimated_nicotine_max": nicotine_range[1],
                "computed_by": rule_set.rule_type,
            },
            total_quantity_kg=total_kg,
            inventory_snapshot={"as_of": timezone.now().isoformat()},
        )
        for grade, pct in components:
            AggregatedGradeComponent.objects.create(
                aggregated_grade=agg,
                base_grade=grade,
                percentage=Decimal(pct),
                kilograms=per_comp_kg.get(grade.id, Decimal("0")),
            )
        outputs.append(agg)

    if rule_set.rule_type == "AI_TREND":
        for category in ["PRIMING", "LUG", "LEAF", "TIP", "STRIP"]:
            top = _pick_top_grades_by_category(category, limit=3)
            if not top:
                continue
            pct = Decimal("100") / Decimal(len(top))
            components = [(g, pct) for g in top]
            create_output(name=f"{category.title()} Blend", components=components, label="Trend Aggregation")

    elif rule_set.rule_type == "AI_SPEC":
        params = rule_set.parameters or {}
        desired_category = params.get("leave_position")  # e.g., LEAF, LUG, TIP, PRIMING
        desired_color = params.get("colour")  # heuristic, maps to grade codes
        top: List[TobaccoGrade] = []
        if desired_category and desired_category in dict(TobaccoGrade.GRADE_CATEGORIES):
            top = _pick_top_grades_by_category(desired_category, limit=3)
        else:
            top = _pick_top_grades_by_category("LEAF", limit=3)

        if desired_color in ("Orange", "O"):
            top = sorted(top, key=lambda g: ("O" in g.grade_code, g.base_price), reverse=True)
        elif desired_color in ("Light", "L"):
            top = sorted(top, key=lambda g: ("L" in g.grade_code, g.base_price), reverse=True)
        elif desired_color in ("Red", "R"):
            top = sorted(top, key=lambda g: ("R" in g.grade_code, g.base_price), reverse=True)

        if top:
            pct = Decimal("100") / Decimal(len(top))
            components = [(g, pct) for g in top]
            create_output(name=f"Spec Blend ({desired_category or 'LEAF'})", components=components, label="Spec Aggregation")

    elif rule_set.rule_type == "USER_RULE":
        params = rule_set.parameters or {}
        comp = params.get("composition", [])  # [{"grade_code"|"grade_id":..., "percentage":...}]
        components: List[Tuple[TobaccoGrade, Decimal]] = []
        for entry in comp:
            grade: TobaccoGrade | None = None
            if entry.get("grade_id"):
                try:
                    grade = TobaccoGrade.objects.get(id=entry["grade_id"], is_active=True)
                except TobaccoGrade.DoesNotExist:
                    continue
            elif entry.get("grade_code"):
                try:
                    grade = TobaccoGrade.objects.get(grade_code=entry["grade_code"], is_active=True)
                except TobaccoGrade.DoesNotExist:
                    continue
            pct = Decimal(str(entry.get("percentage", 0)))
            if grade and pct > 0:
                components.append((grade, pct))
        if components:
            create_output(name=params.get("name", "User Rule Blend"), components=components, label="User Rule")

    elif rule_set.rule_type == "AI_CLIENT_DEMAND":
        open_orders = ClientOrder.objects.filter(
            merchant=merchant, status__in=["PENDING", "CONFIRMED", "IN_PROGRESS"]
        )
        demand_by_category: Dict[str, Decimal] = {}
        for o in open_orders.select_related("grade"):
            category = o.grade.category if o.grade else "LEAF"
            demand_by_category[category] = demand_by_category.get(category, Decimal("0")) + o.requested_quantity
        for category, _qty in sorted(demand_by_category.items(), key=lambda x: x[1], reverse=True):
            top = _pick_top_grades_by_category(category, limit=3)
            if not top:
                continue
            pct = Decimal("100") / Decimal(len(top))
            components = [(g, pct) for g in top]
            create_output(name=f"Demand Blend ({category})", components=components, label="Client Demand")

    return outputs
