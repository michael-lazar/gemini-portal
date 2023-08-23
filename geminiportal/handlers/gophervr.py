from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from geminiportal.aframe import (
    AFrameEntity,
    Position,
    Rotation,
    build_3d_icon,
    build_kiosk,
)
from geminiportal.handlers.base import TemplateHandler
from geminiportal.handlers.gopher import GopherItem


class SpiralLayout:
    """
    Arranges all of the items in a spiral pattern around the center.
    """

    def __init__(
        self,
        initial_radius: float = 5,
        initial_height: float = 0,
        initial_density: int = 12,
        radius_increment: float = 0.2,
        height_increment: float = 0.02,
    ):
        self.initial_radius = initial_radius
        self.initial_height = initial_height
        self.initial_density = initial_density

        self.radius_increment = radius_increment
        self.height_increment = height_increment

    def render(self, items: list[GopherItem]) -> Iterable[AFrameEntity]:
        angle_increment = 2 * math.pi / self.initial_density

        # Generate A-Frame entities for each item.
        radius = self.initial_radius
        height = self.initial_height
        for i, item in enumerate(items):
            # Calculate the x, y position for each box in the spiral.
            x = radius * math.cos(i * angle_increment - math.pi / 2)
            z = radius * math.sin(i * angle_increment - math.pi / 2)

            # Calculate rotation so that the box faces the center.
            y_deg = -math.degrees(i * angle_increment)

            position = Position(x, height, z)
            rotation = Rotation(0, y_deg, 0)

            yield build_3d_icon(item, position, rotation)

            # Increase the radius for the next item to achieve the spiral effect.
            radius += self.radius_increment
            height += self.height_increment


class GopherVRHandler(TemplateHandler):
    template = "proxy/handlers/gopher-vr.html"

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["scene"] = self.layout_scene()
        return context

    def layout_scene(self) -> Iterable[AFrameEntity]:
        yield build_kiosk("Main Gopher Menu")
        layout = SpiralLayout()
        yield from layout.render(self.get_items())

    def get_items(self) -> list[GopherItem]:
        items = []
        for line in self.text.splitlines():
            line = line.rstrip()
            if line == ".":
                break  # Gopher directory EOF

            item = GopherItem.from_item_description(line, self.url)
            if item.url:
                items.append(item)

        return items
