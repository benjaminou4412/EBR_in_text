"""
Woods terrain set card implementations
"""
from ..models import BeingCard, FeatureCard
from ..json_loader import load_path_card_fields #type:ignore


class SitkaBuck(BeingCard):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_path_card_fields("Sitka Buck", "woods")) #type:ignore


class OvergrownThicket(FeatureCard):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_path_card_fields("Overgrown Thicket", "woods")) #type:ignore
