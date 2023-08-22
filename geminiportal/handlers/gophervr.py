from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from geminiportal.aframe import (
    AFrameIcon,
    GopherDir,
    GopherDocument,
    GopherKiosk,
    GopherSearch,
    GopherURL,
    Position,
    Rotation,
)
from geminiportal.handlers.base import TemplateHandler
from geminiportal.handlers.gopher import GopherItem


def build_3d_icon(
    item: GopherItem,
    position: Position,
    rotation: Rotation,
) -> AFrameIcon:
    """
    Construct a 3D icon for the gopher item at the given position.
    """
    if item.item_type == "1":
        return GopherDir.build(position, rotation, item.item_text)
    elif item.item_type == "7":
        return GopherSearch.build(position, rotation, item.item_text)
    elif item.is_url:
        return GopherURL.build(position, rotation, item.item_text)
    else:
        return GopherDocument.build(position, rotation, item.item_text)


class SpiralLayout:
    """
    Arranges all of the items in a spiral pattern around the center.
    """

    def __init__(
        self,
        initial_radius: float = 5,
        initial_density: int = 12,
        radius_increment: float = 0.2,
        height_increment: float = 0.02,
    ):
        self.initial_radius = initial_radius
        self.initial_density = initial_density

        self.radius_increment = radius_increment
        self.height_increment = height_increment

    def render(self, items: list[GopherItem]) -> Iterable[AFrameIcon]:
        angle_increment = 2 * math.pi / self.initial_density

        # Generate A-Frame entities for each item.
        radius = self.initial_radius
        height = 0
        for i, item in enumerate(items):
            # Calculate the x, y position for each box in the spiral.
            x = radius * math.cos(i * angle_increment)
            z = radius * math.sin(i * angle_increment)

            # Calculate rotation so that the box faces the center.
            y_deg = 270 - math.degrees(i * angle_increment)

            position = Position(x, 1 + height, z)
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

    def layout_scene(self) -> Iterable[AFrameIcon]:
        yield GopherKiosk.build(
            position=Position(0, 0, 0),
            text="Home Gopher Server",
        )
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
