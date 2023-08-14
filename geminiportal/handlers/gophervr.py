from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, NamedTuple

from geminiportal.handlers.base import TemplateHandler
from geminiportal.handlers.gopher import GopherItem


class Position(NamedTuple):
    """
    Container for an A-Frame position attribute.
    """

    x: float
    y: float
    z: float

    def __str__(self):
        return f"{self.x} {self.y} {self.z}"


class Rotation(NamedTuple):
    """
    Container for an A-Frame rotation attribute.
    """

    x_deg: float  # Pitch
    y_deg: float  # Yaw
    z_deg: float  # Roll

    def __str__(self):
        return f"{self.x_deg} {self.y_deg} {self.z_deg}"


class AFrameComponent(NamedTuple):
    """
    Container for an A-Frame component.
    """

    tag: str
    attributes: dict

    def get_html(self):
        attr_str = " ".join((f'{k}="{v}"' for k, v in self.attributes.items()))
        return f"<{self.tag} {attr_str}></{self.tag}>"


class Gopher3DIcon(NamedTuple):
    """
    Representation of a gopher item as a series of A-Frame components.
    """

    item: GopherItem
    components: list[AFrameComponent]

    def get_html(self):
        return "\n".join(c.get_html() for c in self.components)


def build_3d_icon(
    item: GopherItem,
    position: Position,
    rotation: Rotation,
) -> Gopher3DIcon:
    """
    Construct a 3D icon for the gopher item at the given position.
    """
    box = AFrameComponent(
        "a-box",
        {
            "position": position,
            "rotation": rotation,
            "depth": 0.1,
            "height": 1,
            "width": 1,
        },
    )

    # Just slightly more than half of the box's depth to avoid z-fighting
    text_offset = 0.11

    text_z = position.z + text_offset * math.cos(math.radians(rotation.y_deg))
    text_x = position.x + text_offset * math.sin(math.radians(rotation.y_deg))

    text = AFrameComponent(
        "a-text",
        {
            "position": Position(text_x, 1, text_z),
            "rotation": rotation,
            "value": item.item_text,
            "align": "center",
            "color": "black",
            "width": 3,
        },
    )

    return Gopher3DIcon(item, [box, text])


class CircularLayout:
    """
    Arranges all of the items around the middle of a geometric circle.
    """

    def __init__(self, radius: float):
        self.radius = radius

    def render(self, items: list[GopherItem]) -> Iterable[Gopher3DIcon]:
        # Calculate angle increment for each box
        angle_increment = 2 * math.pi / len(items)

        # Generate A-Frame entities for each item
        for i, item in enumerate(items):
            # Calculate the x, y position for each box on the circle
            x = self.radius * math.cos(i * angle_increment)
            z = self.radius * math.sin(i * angle_increment)

            # Calculate rotation so that the box faces the center
            y_deg = 270 - math.degrees(i * angle_increment)

            position = Position(x, 1, z)
            rotation = Rotation(0, y_deg, 0)
            yield build_3d_icon(item, position, rotation)


class GopherVRHandler(TemplateHandler):
    template = "proxy/handlers/gopher-vr.html"

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["scene"] = self.layout_scene()
        return context

    def layout_scene(self) -> list[Gopher3DIcon]:
        items = list(self.iter_content())
        layout = CircularLayout(radius=10)
        scene = list(layout.render(items))
        return scene

    def iter_content(self) -> Iterable[GopherItem]:
        for line in self.text.splitlines():
            line = line.rstrip()
            if line == ".":
                break  # Gopher directory EOF

            item = GopherItem.from_item_description(line, self.url)
            if item.url:
                yield item
