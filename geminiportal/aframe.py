from __future__ import annotations

from dataclasses import dataclass, field

from geminiportal.handlers.gopher import GopherItem

OBJ_SCALE = 0.003

COLOR_TEXT = "#FFFFFF"
COLOR_GOPHER_KIOSK = "#960000"
COLOR_GOPHER_DOCUMENT = "#df7400"
COLOR_GOPHER_SOUND = "#df7400"
COLOR_GOPHER_DIR = "#0068a8"
COLOR_GOPHER_URL = "#368011"
COLOR_GOPHER_SEARCH = "#871969"
COLOR_GOPHER_TELNET = "#E1B000"


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
        obj: str,
        color: str,
    ) -> AFrameEntity:
        """
        Construct an obj model entity.
        """
        return cls(
            "a-entity",
            attributes={
                "position": position,
                # TODO: Need to mirror the objects so I can avoid this hack
                "rotation": rotation + Rotation(x_deg=180),
                "obj-model": f"obj: {obj}",
                "material": f"color: {color}",
                "scale": Scale.const(OBJ_SCALE),
            },
        )

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
                "color": COLOR_TEXT,
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
    color = COLOR_GOPHER_DIR

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            obj="#dir-obj",
            color=self.color,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"
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
    color = COLOR_GOPHER_DOCUMENT

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            obj="#document-obj",
            color=self.color,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"
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
    color = COLOR_GOPHER_URL


class GopherSearch(GopherIcon):
    color = COLOR_GOPHER_SEARCH

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            obj="#search-obj",
            color=self.color,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"
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
    color = COLOR_GOPHER_SOUND

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            obj="#sound-obj",
            color=self.color,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"
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
    color = COLOR_GOPHER_TELNET

    def build(self) -> AFrameEntity:
        obj = AFrameEntity.build_obj(
            position=self.position,
            rotation=self.rotation,
            obj="#telnet-obj",
            color=self.color,
        )
        obj.attributes["navigate-on-click"] = f"url: {self.item.url.get_proxy_url(vr=1)}"
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
        obj="#kiosk-obj",
        color=COLOR_GOPHER_KIOSK,
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
