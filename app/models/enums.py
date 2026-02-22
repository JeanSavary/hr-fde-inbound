from enum import Enum


class EquipmentType(str, Enum):
    """Equipment type for loads. Values: dry_van, reefer, flatbed,
    step_deck, power_only."""

    DRY_VAN = "dry_van"
    REEFER = "reefer"
    FLATBED = "flatbed"
    STEP_DECK = "step_deck"
    POWER_ONLY = "power_only"


class OfferType(str, Enum):
    INITIAL = "initial"
    COUNTER = "counter"
    FINAL = "final"


class OfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Verdict(str, Enum):
    ACCEPT = "accept"
    COUNTER = "counter"
    REJECT = "reject"


class CallOutcome(str, Enum):
    BOOKED = "booked"
    NEGOTIATION_FAILED = "negotiation_failed"
    NO_LOADS = "no_loads_available"
    INVALID_CARRIER = "invalid_carrier"
    CARRIER_THINKING = "carrier_thinking"
    TRANSFERRED_OPS = "transferred_to_ops"
    DROPPED = "dropped_call"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    AGGRESSIVE = "aggressive"
    CONFUSED = "confused"
