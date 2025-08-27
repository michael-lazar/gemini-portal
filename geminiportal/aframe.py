from __future__ import annotations

from dataclasses import dataclass, field

from geminiportal.handlers.gopher import GopherItem
from geminiportal.urls import URLReference


@dataclass
class Position:
    """
    Container for an A-Frame position component.
    """

    x: float = 0
    y: float = 0
    z: float = 0

    def __str__(self):
        return f"{self.x:.4f} {self.y:.4f} {self.z:.4f}"

    def __add__(self, other: Position) -> Position:
        return Position(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )


@dataclass
class Rotation:
    """
    Container for an A-Frame rotation component.
    """

    x_deg: float = 0  # Pitch
    y_deg: float = 0  # Yaw
    z_deg: float = 0  # Roll

    def __str__(self):
        return f"{self.x_deg:.4f} {self.y_deg:.4f} {self.z_deg:.4f}"

    def __add__(self, other: Rotation) -> Rotation:
        return Rotation(
            self.x_deg + other.x_deg,
            self.y_deg + other.y_deg,
            self.z_deg + other.z_deg,
        )


@dataclass
class Scale:
    """
    Container for an A-Frame scale component.
    """

    x: float = 0
    y: float = 0
    z: float = 0

    def __str__(self):
        return f"{self.x:.4f} {self.y:.4f} {self.z:.4f}"

    def __add__(self, other: Scale) -> Scale:
        return Scale(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )

    @classmethod
    def const(cls, value: float) -> Scale:
        return cls(value, value, value)


@dataclass
class Color:
    """
    Container for an A-Frame HTML color.
    """

    r: int
    g: int
    b: int

    def __str__(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def adjust(self, value: int = -10) -> Color:
        r = min(max(0, self.r + value), 255)
        g = min(max(0, self.g + value), 255)
        b = min(max(0, self.b + value), 255)
        return Color(r, g, b)


@dataclass
class AFrameEntity:
    """
    Container for an A-Frame component.
    """

    tag: str
    attributes: dict = field(default_factory=dict)
    children: list[AFrameEntity] = field(default_factory=list)

    def __str__(self):
        attr_str = " ".join((f'{k}="{v}"' for k, v in self.attributes.items()))
        children_str = "".join(str(c) for c in self.children)
        return f"<{self.tag} {attr_str}>{children_str}</{self.tag}>"

    @classmethod
    def build_obj(
        cls,
        position: Position,
        rotation: Rotation,
        color: Color,
        obj: str,
        url: URLReference | None = None,
    ) -> AFrameEntity:
        """
        Construct an obj model entity.
        """
        attributes = {
            "position": position,
            # TODO: Need to mirror the objects so I can avoid this hack
            "rotation": rotation + Rotation(x_deg=180),
            "obj-model": f"obj: {obj}",
            "material": f"color: {color}",
            "scale": Scale.const(0.003),
        }
        if url:
            proxy_url = url.get_proxy_url(vr=1)
            selected_color = color.adjust(30)
            attributes |= {
                "class": "clickable",
                "link-obj": f"url: {proxy_url}; selectedColor: {selected_color}",
            }

        entity = cls("a-entity", attributes)
        return entity

    @classmethod
    def build_text(
        cls,
        position: Position,
        rotation: Rotation,
        text: str,
        width: float,
    ) -> AFrameEntity:
        """
        Construct a text entity.
        """
        return cls(
            "a-text",
            {
                "position": position,
                "rotation": rotation + Rotation(x_deg=180),
                "width": width,
                "value": text,
                "color": Color(255, 255, 255),
                "align": "center",
                "wrap-count": 12,
            },
        )


class GopherIcon:
    """
    Builds the A-Frame representation for a given gopher menu item.
    """

    def __init__(self, item: GopherItem, position: Position, rotation: Rotation):
        self.item = item
        self.position = position
        self.rotation = rotation

    def build(self) -> AFrameEntity:
        raise NotImplementedError()


class GopherDir(GopherIcon):
    color = Color(0, 104, 168)

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            color=self.color,
            obj="#dir-obj",
            url=self.item.url,
        )
        obj.children.append(
            AFrameEntity.build_text(
                position=Position(0, -201, -85),
                rotation=Rotation(),
                text=self.item.item_text,
                width=500,
            )
        )
        return obj


class GopherDocument(GopherIcon):
    color = Color(223, 116, 0)

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            color=self.color,
            obj="#document-obj",
            url=self.item.url,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"  # type: ignore
        obj.children.append(
            AFrameEntity.build_text(
                position=Position(0, -213, -57),
                rotation=Rotation(),
                text=self.item.item_text,
                width=500,
            )
        )
        return obj


class GopherURL(GopherDocument):
    color = Color(54, 128, 17)


class GopherSearch(GopherIcon):
    color = Color(135, 25, 105)

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            color=self.color,
            obj="#search-obj",
            url=self.item.url,
        )
        obj.children.append(
            AFrameEntity.build_text(
                position=Position(0, -273, -80),
                rotation=Rotation(),
                text=self.item.item_text,
                width=500,
            )
        )
        return obj


class GopherSound(GopherIcon):
    color = Color(223, 116, 0)

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            color=self.color,
            obj="#sound-obj",
            url=self.item.url,
        )
        obj.children.append(
            AFrameEntity.build_text(
                position=Position(0, -192, -157),
                rotation=Rotation(),
                text=self.item.item_text,
                width=500,
            )
        )
        return obj


class GopherTelnet(GopherIcon):
    color = Color(255, 178, 0)

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            color=self.color,
            obj="#telnet-obj",
            url=self.item.url,
        )
        obj.children.append(
            AFrameEntity.build_text(
                position=Position(0, -236, -87),
                rotation=Rotation(),
                text=self.item.item_text,
                width=500,
            )
        )
        return obj


def build_3d_icon(
    item: GopherItem,
    position: Position,
    rotation: Rotation,
) -> AFrameEntity:
    """
    Construct a 3D icon for the gopher item at the given position.
    """
    icon_class: type[GopherIcon]

    if item.item_type == "1":
        icon_class = GopherDir
    elif item.is_url:
        icon_class = GopherURL
    elif item.item_type == "7":
        icon_class = GopherSearch
    elif item.item_type == "8":
        icon_class = GopherTelnet
    elif item.item_type == "s":
        icon_class = GopherSound
    else:
        icon_class = GopherDocument

    return icon_class(item, position, rotation).build()


def build_kiosk(text: str) -> AFrameEntity:
    obj = AFrameEntity.build_obj(
        position=Position(),
        rotation=Rotation(),
        color=Color(150, 0, 0),
        obj="#kiosk-obj",
    )
    obj.children.extend(
        [
            AFrameEntity.build_text(
                position=Position(0, -385, -245),
                rotation=Rotation(0, 0, 0),
                text=text,
                width=420,
            ),
            AFrameEntity.build_text(
                position=Position(-218, -385, -22),
                rotation=Rotation(0, 90, 0),
                text=text,
                width=420,
            ),
            AFrameEntity.build_text(
                position=Position(0, -385, 189),
                rotation=Rotation(0, 180, 0),
                text=text,
                width=420,
            ),
            AFrameEntity.build_text(
                position=Position(218, -385, -35),
                rotation=Rotation(0, 270, 0),
                text=text,
                width=420,
            ),
        ]
    )
    return obj
