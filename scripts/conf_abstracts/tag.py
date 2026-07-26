"""Resolve society and elasmo flag for an abstract record."""
from conf_abstracts.config import ELASMO_SOCIETIES, ELASMO_MEETINGS


def _first(seq):
    return seq[0] if seq else None


def resolve(record: dict, meeting: str) -> dict:
    """Populate society, society_basis, is_elasmo, elasmo_basis.

    Priority for society: explicit session prefix/award (societies_explicit)
    then LLM content inference (society_inferred).
    is_elasmo: AES in societies OR meeting in {SI, EEA}.
    """
    explicit = record.get("societies_explicit") or []
    award = record.get("award")
    inferred = record.get("society_inferred")

    society = None
    society_basis = None
    # explicit prefix wins; award is also explicit but slightly lower priority
    if explicit:
        society = _first(explicit)
        society_basis = "award" if (award and society in award) and len(explicit) == 1 else "session_prefix"
    elif inferred:
        society = inferred
        society_basis = "content"

    # elasmo determination + provenance
    is_elasmo = 0
    elasmo_basis = None
    if meeting in ELASMO_MEETINGS:
        is_elasmo = 1
        elasmo_basis = "meeting"
    elif any(s in ELASMO_SOCIETIES for s in explicit):
        is_elasmo = 1
        # if AES came via award suffix, basis = award
        elasmo_basis = "award" if (award and "AES" in award) else "session_prefix"
    elif inferred in ELASMO_SOCIETIES:
        is_elasmo = 1
        elasmo_basis = "content"

    record["society"] = society
    record["society_basis"] = society_basis
    record["is_elasmo"] = is_elasmo
    record["elasmo_basis"] = elasmo_basis
    return record
