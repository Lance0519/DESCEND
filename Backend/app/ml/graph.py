"""Family graph traversal logic for T2DM hereditary risk computation.

Builds a directed graph of family relationships and computes distance-weighted
risk metrics used by the prediction pipeline.
"""

from __future__ import annotations

import networkx as nx

from .feature_builder import FAMILY_ORDER, STATUS_MAP, normalize_family_status


FAMILY_EDGES = [
    ("maternalGrandmother", "mother"),
    ("maternalGrandfather", "mother"),
    ("paternalGrandmother", "father"),
    ("paternalGrandfather", "father"),
    ("mother", "user"),
    ("father", "user"),
]


def build_family_graph(family_history: dict) -> nx.DiGraph:
    """Construct a directed graph encoding family T2DM status and lineage distance."""
    graph = nx.DiGraph()
    graph.add_edges_from(FAMILY_EDGES)

    for member in FAMILY_ORDER:
        graph.nodes[member]["status"] = normalize_family_status(family_history.get(member, "unknown"))

    graph.nodes["user"]["status"] = "no"
    return graph


def _count_status(family_history: dict, members: list[str], target: str) -> int:
    return sum(
        1
        for member in members
        if normalize_family_status(family_history.get(member, "unknown")) == target
    )


def derive_family_metrics(
    family_history: dict,
    extended_diabetes_count: int = 0,
) -> dict:
    """Compute distance-weighted family risk metrics from the family graph.

    ``extended_diabetes_count`` should match sibling + aunt/uncle T2DM counts used
    in training (capped) so lineageRiskIndex reflects generational burden and
    lateral family load consistently at inference time.

    Returns a dict containing weighted scores, lineage splits, degree counts,
    and a composite lineage risk index.
    """
    graph = build_family_graph(family_history)
    weighted_score = 0.0
    maternal_score = 0.0
    paternal_score = 0.0

    for member in FAMILY_ORDER:
        distance = nx.shortest_path_length(graph, source=member, target="user")
        status_key = normalize_family_status(family_history.get(member, "unknown"))
        status_value = STATUS_MAP.get(status_key, 0.35)
        contribution = status_value / distance
        weighted_score += contribution

        if member.startswith("maternal") or member == "mother":
            maternal_score += contribution
        else:
            paternal_score += contribution

    first_degree_yes = _count_status(family_history, ["mother", "father"], "yes")
    second_degree_yes = _count_status(
        family_history,
        [
            "maternalGrandmother",
            "maternalGrandfather",
            "paternalGrandmother",
            "paternalGrandfather",
        ],
        "yes",
    )
    unknown_relatives = _count_status(family_history, FAMILY_ORDER, "unknown")
    diabetic_relatives = _count_status(family_history, FAMILY_ORDER, "yes")
    ext = min(max(int(extended_diabetes_count), 0), 6)
    # Generational + lateral burden: distance-weighted tree, explicit 1st/2nd degree
    # counts, and capped extended-family diabetes count (siblings + aunts/uncles).
    lineage_risk_index = round(
        weighted_score * 0.36
        + float(first_degree_yes) * 0.30
        + float(second_degree_yes) * 0.20
        + float(ext) * 0.07,
        2,
    )

    # Genetic propagation style probability: multiplicative per-relative transmission
    # P_inherited = 1 - prod_{d=1..D} (1 - rho_d)^{F_d}
    # Default per-relative transmission probabilities (conservative literature-informed priors)
    rho_1 = 0.18
    rho_2 = 0.08
    rho_3 = 0.04
    # F1 = first-degree yes, F2 = second-degree yes, F3 = capped extended-family count
    f1 = int(first_degree_yes)
    f2 = int(second_degree_yes)
    f3 = int(ext)
    prod = 1.0
    if f1 > 0:
        prod *= (1.0 - rho_1) ** f1
    if f2 > 0:
        prod *= (1.0 - rho_2) ** f2
    if f3 > 0:
        prod *= (1.0 - rho_3) ** f3
    propagation_probability = round(1.0 - prod, 4)

    return {
        "weightedFamilyScore": round(weighted_score, 2),
        "maternalScore": round(maternal_score, 2),
        "paternalScore": round(paternal_score, 2),
        "firstDegreeYesCount": first_degree_yes,
        "secondDegreeYesCount": second_degree_yes,
        "unknownRelativesCount": unknown_relatives,
        "diabeticRelativesCount": diabetic_relatives,
        "lineageRiskIndex": lineage_risk_index,
        "propagationProbability": propagation_probability,
    }
