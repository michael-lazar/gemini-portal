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
            "height": 2,
            "width": 2,
            "color": "orange",
        },
    )

    text_offset = 0.05

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
            "width": 2,
            "wrap-count": 15,
        },
    )

    return Gopher3DIcon([box, text])


def build_kiosk(position: Position) -> Gopher3DIcon:
    cone = AFrameComponent(
        "a-cone",
        {
            "position": position,
            "radius-bottom": 1,
            "radius-top": 0,
            "segmentsRadial": 4,
            "height": 6,
            "color": "red",
        },
    )
    box = AFrameComponent(
        "a-box",
        {
            "position": Position(position.x, position.y + 1.5, position.z),
            "height": 0.75,
            "width": 1,
            "depth": 1,
            "color": "red",
        },
    )

    return Gopher3DIcon([cone, box])


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


class SpiralLayout:
    """
    Arranges all of the items in a spiral pattern around the center.
    """

    def __init__(
        self,
        initial_radius: float = 5,
        spacing: float = 0.4,
        increment: float = 10.0,
    ):
        self.initial_radius = initial_radius
        self.spacing = spacing
        self.increment = increment

    def render(self, items: list[GopherItem]) -> Iterable[Gopher3DIcon]:
        angle_increment = 2 * math.pi / self.increment

        # Generate A-Frame entities for each item.
        radius = self.initial_radius
        for i, item in enumerate(items):
            # Calculate the x, y position for each box in the spiral.
            x = radius * math.cos(i * angle_increment)
            z = radius * math.sin(i * angle_increment)

            # Calculate rotation so that the box faces the center.
            y_deg = 270 - math.degrees(i * angle_increment)

            position = Position(x, 1, z)
            rotation = Rotation(0, y_deg, 0)
            yield build_3d_icon(item, position, rotation)

            # Increase the radius for the next item to achieve the spiral effect.
            radius += self.spacing


class GopherVRHandler(TemplateHandler):
    template = "proxy/handlers/gopher-vr.html"

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["scene"] = self.layout_scene()
        return context

    def layout_scene(self) -> Iterable[Gopher3DIcon]:
        yield build_kiosk(Position(0, 0, 0))

        # layout = CircularLayout(radius=10)
        layout = SpiralLayout(initial_radius=5, spacing=0.4)
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
