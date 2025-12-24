from dataclasses import dataclass, field
from typing import Literal, Set, List

Category = Literal["bottom", "mid", "outer", "shoes", "accessory"]


@dataclass
class ClothingItem:
    code: str
    title: str
    category: Category
    warmth: float
    rain_protect: bool = False
    wind_protect: bool = False
    style_tags: Set[str] = field(default_factory=set)  # {"casual", "office", "sport"}


ITEMS: List[ClothingItem] = [
    # ==================== НИЗ (bottom) ====================

    ClothingItem(
        code="jeans_straight",
        title="прямые джинсы",
        category="bottom",
        warmth=1.8,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="jeans_wide",
        title="широкие джинсы",
        category="bottom",
        warmth=1.7,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="trousers_tailored",
        title="классические брюки",
        category="bottom",
        warmth=1.9,
        style_tags={"office"},
    ),
    ClothingItem(
        code="trousers_wool",
        title="шерстяные брюки",
        category="bottom",
        warmth=2.3,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="linen_trousers",
        title="лёгкие льняные брюки",
        category="bottom",
        warmth=0.8,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="leggings",
        title="леггинсы",
        category="bottom",
        warmth=1.2,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="thermal_leggings",
        title="термолеггинсы",
        category="bottom",
        warmth=2.2,
        style_tags={"casual", "sport"},
    ),

    # юбки
    ClothingItem(
        code="skirt_midi_wool",
        title="тёплая миди-юбка",
        category="bottom",
        warmth=1.9,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="skirt_midi_light",
        title="лёгкая миди-юбка",
        category="bottom",
        warmth=1.1,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="skirt_mini_dense",
        title="плотная мини-юбка с колготками",
        category="bottom",
        warmth=1.6,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="skirt_silk",
        title="шелковая юбка миди",
        category="bottom",
        warmth=0.9,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="shorts_denim",
        title="джинсовые шорты",
        category="bottom",
        warmth=0.6,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="shorts_linen",
        title="лёгкие шорты",
        category="bottom",
        warmth=0.4,
        style_tags={"casual"},
    ),

    # ==================== СРЕДНИЙ СЛОЙ / ВЕРХ (mid) ====================

    ClothingItem(
        code="tshirt_basic",
        title="базовая футболка",
        category="mid",
        warmth=0.7,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="tshirt_fitted",
        title="облегающая футболка",
        category="mid",
        warmth=0.7,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="longsleeve",
        title="лонгслив",
        category="mid",
        warmth=1.0,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="blouse_light",
        title="лёгкая блузка",
        category="mid",
        warmth=0.8,
        style_tags={"office"},
    ),
    ClothingItem(
        code="shirt_oversized",
        title="оверсайз рубашка",
        category="mid",
        warmth=1.0,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="sweatshirt",
        title="свитшот",
        category="mid",
        warmth=1.5,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="hoodie",
        title="худи",
        category="mid",
        warmth=1.6,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="sweater_wool",
        title="шерстяной свитер",
        category="mid",
        warmth=2.1,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="turtleneck_thin",
        title="тонкая водолазка",
        category="mid",
        warmth=1.4,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="turtleneck_warm",
        title="тёплая водолазка",
        category="mid",
        warmth=1.9,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="cardigan_long",
        title="длинный кардиган",
        category="mid",
        warmth=1.6,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="fleece",
        title="флиска",
        category="mid",
        warmth=1.9,
        style_tags={"sport", "casual"},
    ),
    ClothingItem(
        code="thermal_top",
        title="термокофта",
        category="mid",
        warmth=2.0,
        style_tags={"sport", "casual"},
    ),
    ClothingItem(
        code="dress_cotton_midi",
        title="хлопковое платье миди и копроновые колготки",
        category="mid",
        warmth=1.4,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="dress_wool_midi",
        title="тёплое вязаное платье и тёплые колготки",
        category="mid",
        warmth=2.2,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="dress_silk_midi",
        title="шёлковое платье миди",
        category="mid",
        warmth=1.0,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="dress_mini_party",
        title="мини-платье",
        category="mid",
        warmth=0.9,
        style_tags={"casual"},
    ),

    # ==================== ВЕРХНЯЯ ОДЕЖДА (outer) ====================

    ClothingItem(
        code="denim_jacket",
        title="джинсовка",
        category="outer",
        warmth=1.2,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="leather_jacket",
        title="кожаная куртка",
        category="outer",
        warmth=1.6,
        wind_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="blazer",
        title="жакет/блейзер",
        category="outer",
        warmth=1.3,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="trench",
        title="тренч",
        category="outer",
        warmth=1.8,
        wind_protect=True,
        rain_protect=True,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="bomber",
        title="бомбер",
        category="outer",
        warmth=1.7,
        wind_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="light_puffer",
        title="лёгкий пуховик",
        category="outer",
        warmth=2.3,
        wind_protect=True,
        rain_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="mid_puffer",
        title="демисезонный пуховик",
        category="outer",
        warmth=2.8,
        wind_protect=True,
        rain_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="parka",
        title="парка",
        category="outer",
        warmth=3.0,
        wind_protect=True,
        rain_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="wool_coat",
        title="шерстяное пальто",
        category="outer",
        warmth=2.7,
        wind_protect=True,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="teddy_coat",
        title="тедди-пальто",
        category="outer",
        warmth=3.0,
        wind_protect=True,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="winter_puffer",
        title="зимний пуховик",
        category="outer",
        warmth=3.7,
        wind_protect=True,
        rain_protect=True,
        style_tags={"casual"},
    ),

    # ==================== ОБУВЬ (shoes) ====================

    ClothingItem(
        code="sneakers_basic",
        title="кроссовки",
        category="shoes",
        warmth=1.0,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="sneakers_light",
        title="лёгкие кеды",
        category="shoes",
        warmth=0.7,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="ballet_flats",
        title="балетки",
        category="shoes",
        warmth=0.9,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="loafers",
        title="лоферы",
        category="shoes",
        warmth=1.1,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="ankle_boots_heel",
        title="ботинки на каблуке",
        category="shoes",
        warmth=1.9,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="ankle_boots_flat",
        title="ботинки без каблука",
        category="shoes",
        warmth=1.8,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="knee_boots",
        title="сапоги до колена",
        category="shoes",
        warmth=2.4,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="overknee_boots",
        title="ботфорты",
        category="shoes",
        warmth=2.6,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="winter_boots",
        title="зимние ботинки",
        category="shoes",
        warmth=2.8,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="ugg_boots",
        title="угги",
        category="shoes",
        warmth=3.0,
        style_tags={"casual"},
    ),
    ClothingItem(
        code="rubber_boots",
        title="резиновые сапоги",
        category="shoes",
        warmth=1.5,
        rain_protect=True,
        style_tags={"casual"},
    ),

    # ==================== АКСЕССУАРЫ (accessory) ====================

    ClothingItem(
        code="beanie",
        title="шапка-бини",
        category="accessory",
        warmth=0.9,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="beret",
        title="берет",
        category="accessory",
        warmth=0.7,
        style_tags={"office", "casual"},
    ),
    ClothingItem(
        code="cap",
        title="кепка",
        category="accessory",
        warmth=0.3,
        style_tags={"casual", "sport"},
    ),
    ClothingItem(
        code="scarf_wool",
        title="тёплый шарф",
        category="accessory",
        warmth=0.9,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="scarf_light",
        title="лёгкий шарфик",
        category="accessory",
        warmth=0.4,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="gloves",
        title="перчатки",
        category="accessory",
        warmth=0.6,
        style_tags={"casual", "office"},
    ),
    ClothingItem(
        code="mittens",
        title="варежки",
        category="accessory",
        warmth=0.8,
        style_tags={"casual", "sport"},
    ),
]
