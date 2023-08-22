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

    x: float = 0
    y: float = 0
    z: float = 0

    def __str__(self):
        return f"{self.x} {self.y} {self.z}"


class Rotation(NamedTuple):
    """
    Container for an A-Frame rotation attribute.
    """

    x_deg: float = 0  # Pitch
    y_deg: float = 0  # Yaw
    z_deg: float = 0  # Roll

    def __str__(self):
        return f"{self.x_deg} {self.y_deg} {self.z_deg}"


class Scale(NamedTuple):
    """
    Container for an A-Frame scale attribute.
    """

    x: float = 0
    y: float = 0
    z: float = 0

    def __str__(self):
        return f"{self.x} {self.y} {self.z}"

    @classmethod
    def from_scalar(cls, value: float) -> Scale:
        return cls(value, value, value)


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

    def __add__(self, other):
        return Gopher3DIcon(*self.components, *other.components)


def build_3d_icon(
    item: GopherItem,
    position: Position,
    rotation: Rotation,
) -> Gopher3DIcon:
    """
    Construct a 3D icon for the gopher item at the given position.
    """
    if item.item_type == "1":
        depth = 0.5
        color = "#0068a8"
    elif item.item_type == "h":
        depth = 0.1
        color = "#368011"
    else:
        depth = 0.1
        color = "#df7400"

    box = AFrameComponent(
        "a-box",
        {
            "position": position,
            "rotation": rotation,
            "depth": depth,
            "height": 1.5,
            "width": 2,
            "color": color,
        },
    )

    text_offset = depth / 2
    text_position = Position(
        position.x + text_offset * math.sin(math.radians(rotation.y_deg)),
        position.y,
        position.z + text_offset * math.cos(math.radians(rotation.y_deg)),
    )

    text = AFrameComponent(
        "a-text",
        {
            "position": text_position,
            "rotation": rotation,
            "value": item.item_text,
            "align": "center",
            "color": "white",
            "width": 2,
            "wrap-count": 15,
        },
    )
    return Gopher3DIcon([box, text])


def build_kiosk(
    position: Position,
    text: str = "Home Gopher Server",
) -> Gopher3DIcon:
    cone = AFrameComponent(
        "a-cone",
        {
            "position": position,
            "radius-bottom": 1.2,
            "radius-top": 0,
            "segmentsRadial": 4,
            "height": 5.5,
            "color": "#960000",
        },
    )

    box_pos = Position(position.x, position.y + 1.2, position.z)
    box_width = 1.3
    box_depth = 1.3
    box_height = 1.0

    box = AFrameComponent(
        "a-box",
        {
            "position": box_pos,
            "height": box_height,
            "width": box_width,
            "depth": box_depth,
            "color": "#960000",
        },
    )

    text_attr = {
        "value": text,
        "align": "center",
        "color": "white",
        "width": box_width,
        "wrap-count": 15,
    }

    text1 = AFrameComponent(
        "a-text",
        {
            "position": Position(box_pos.x, box_pos.y, box_pos.z + box_depth / 2),
            "rotation": Rotation(0, 0, 0),
            **text_attr,
        },
    )
    text2 = AFrameComponent(
        "a-text",
        {
            "position": Position(box_pos.x, box_pos.y, box_pos.z - box_depth / 2),
            "rotation": Rotation(0, 180, 0),
            **text_attr,
        },
    )
    text3 = AFrameComponent(
        "a-text",
        {
            "position": Position(box_pos.x - box_width / 2, box_pos.y, box_pos.z),
            "rotation": Rotation(0, -90, 0),
            **text_attr,
        },
    )
    text4 = AFrameComponent(
        "a-text",
        {
            "position": Position(box_pos.x + box_width / 2, box_pos.y, box_pos.z),
            "rotation": Rotation(0, 90, 0),
            **text_attr,
        },
    )
    return Gopher3DIcon([cone, box, text1, text2, text3, text4])


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

    def render(self, items: list[GopherItem]) -> Iterable[Gopher3DIcon]:
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

    def layout_scene(self) -> Iterable[Gopher3DIcon]:
        yield build_kiosk(Position(0, 0, 0))

        # layout = CircularLayout(radius=10)
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
