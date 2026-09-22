from typing import List

from app.models.tick import Tick
from app.models.footprint import FootprintBar


class FootprintBuilder:

    def __init__(self):
        pass


    def build(self, ticks: List[Tick]) -> FootprintBar:
        raise NotImplementedError(
            "FootprintBuilder implementation pending"
        )