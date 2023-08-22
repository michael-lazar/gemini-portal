from __future__ import annotations

import math
from typing import NamedTuple

COLOR_TEXT = "#FFFFFF"
COLOR_GOPHER_KIOSK = "#960000"
COLOR_GOPHER_DOCUMENT = "#df7400"
COLOR_GOPHER_DIR = "#0068a8"
COLOR_GOPHER_URL = "#368011"
COLOR_GOPHER_SEARCH = "#871969"
COLOR_GOPHER_TELNET = "#E1B000"


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


class AFrameIcon:
    """
    Representation of a 3D icon as a series of A-Frame components.
    """

    components: list[AFrameComponent]

    def __init__(self, components):
        self.components = components

    def get_html(self):
        return "\n".join(c.get_html() for c in self.components)


class InfoCube(AFrameIcon):
    """
    A 3D box with words on all sides, excluding the top and bottom.
    """

    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
        width: float,
        height: float,
        color: str,
    ):
        cube = AFrameComponent(
            "a-box",
            {
                "position": position,
                "rotation": rotation,
                "height": height,
                "width": width,
                "depth": width,
                "color": color,
            },
        )
        text1 = AFrameComponent(
            "a-text",
            {
                "position": Position(position.x, position.y, position.z + width / 2),
                "rotation": Rotation(0, 0, 0),
                "value": text,
                "align": "center",
                "color": COLOR_TEXT,
                "width": width,
                "wrap-count": 15,
            },
        )
        text2 = AFrameComponent(
            "a-text",
            {
                "position": Position(position.x, position.y, position.z - width / 2),
                "rotation": Rotation(0, 180, 0),
                "value": text,
                "align": "center",
                "color": COLOR_TEXT,
                "width": width,
                "wrap-count": 15,
            },
        )
        text3 = AFrameComponent(
            "a-text",
            {
                "position": Position(position.x - width / 2, position.y, position.z),
                "rotation": Rotation(0, -90, 0),
                "value": text,
                "align": "center",
                "color": COLOR_TEXT,
                "width": width,
                "wrap-count": 15,
            },
        )
        text4 = AFrameComponent(
            "a-text",
            {
                "position": Position(position.x + width / 2, position.y, position.z),
                "rotation": Rotation(0, 90, 0),
                "value": text,
                "align": "center",
                "color": COLOR_TEXT,
                "width": width,
                "wrap-count": 15,
            },
        )
        return cls([cube, text1, text2, text3, text4])


class Plaque(AFrameIcon):
    """
    A generic 3D rectangle with words on the front face.
    """

    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
        width: float,
        height: float,
        depth: float,
        color: str,
    ):
        box = AFrameComponent(
            "a-box",
            {
                "position": position,
                "rotation": rotation,
                "depth": depth,
                "height": height,
                "width": width,
                "color": color,
            },
        )
        text1 = AFrameComponent(
            "a-text",
            {
                "position": Position(
                    position.x + depth / 2 * math.sin(math.radians(rotation.y_deg)),
                    position.y,
                    position.z + depth / 2 * math.cos(math.radians(rotation.y_deg)),
                ),
                "rotation": rotation,
                "value": text,
                "align": "center",
                "color": COLOR_TEXT,
                "width": width,
                "wrap-count": 15,
            },
        )
        return cls([box, text1])


class GopherKiosk(AFrameIcon):
    @classmethod
    def build(cls, position: Position, text: str):
        cone = AFrameComponent(
            "a-cone",
            {
                "position": position,
                "radius-bottom": 1.2,
                "radius-top": 0,
                "segmentsRadial": 4,
                "height": 5.5,
                "color": COLOR_GOPHER_KIOSK,
            },
        )
        cube = InfoCube.build(
            position=Position(position.x, position.y + 1.2, position.z),
            rotation=Rotation(0, 0, 0),
            text=text,
            width=1.3,
            height=1.0,
            color=COLOR_GOPHER_KIOSK,
        )
        return cls([cone, *cube.components])


class GopherDocument(AFrameIcon):
    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
    ):
        plaque = Plaque.build(
            position=position,
            rotation=rotation,
            text=text,
            width=2,
            height=1.5,
            depth=0.1,
            color=COLOR_GOPHER_DOCUMENT,
        )
        return cls(plaque.components)


class GopherDir(AFrameIcon):
    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
    ):
        plaque = Plaque.build(
            position=position,
            rotation=rotation,
            text=text,
            width=2,
            height=1.5,
            depth=0.5,
            color=COLOR_GOPHER_DIR,
        )
        return cls(plaque.components)


class GopherURL(AFrameIcon):
    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
    ):
        plaque = Plaque.build(
            position=position,
            rotation=rotation,
            text=text,
            width=2,
            height=1.5,
            depth=0.1,
            color=COLOR_GOPHER_URL,
        )
        return cls(plaque.components)


class GopherSearch(AFrameIcon):
    @classmethod
    def build(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
        width: float = 2.0,
        height: float = 1.5,
        depth: float = 0.5,
    ):
        plaque = Plaque.build(
            position=position,
            rotation=rotation,
            text=text,
            width=width,
            height=height,
            depth=depth,
            color=COLOR_GOPHER_SEARCH,
        )

        x = position.x
        y = position.y
        z = position.z

        x_offset = width / 2
        y_offset = height / 2
        z_offset = depth / 2

        triangle1 = AFrameComponent(
            "a-triangle",
            {
                "position": Position(x + z_offset, y + y_offset, z),
                "rotation": rotation,
                "vertex-a": Position(-x_offset, 0, 0),
                "vertex-b": Position(x_offset, 0, 0),
                "vertex-c": Position(x_offset, height / 4, 0),
                "color": COLOR_GOPHER_SEARCH,
            },
        )
        triangle2 = AFrameComponent(
            "a-triangle",
            {
                "position": Position(x - z_offset, y + y_offset, z),
                "rotation": rotation,
                "vertex-a": Position(-x_offset, 0, 0),
                "vertex-b": Position(x_offset, height / 4, 0),
                "vertex-c": Position(x_offset, 0, 0),
                "color": COLOR_GOPHER_SEARCH,
            },
        )
        return cls([*plaque.components, triangle1, triangle2])
