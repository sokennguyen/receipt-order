"""Static menu and note data."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import MenuItem


@dataclass(frozen=True)
class DishMeta:
    """Canonical text metadata for a dish."""

    display_name: str
    aliases: list[str]
    print_label: str | None = None


NOTE_CATALOG: dict[str, str] = {
    "less_spicy": "Less Spicy",
    "less_less_spicy": "Less Less Spicy",
    "more_spicy": "More Spicy",
    "more_more_spicy": "More More Spicy",
    "no_mushroom": "No Mushroom",
    "no_onions": "No Onions",
    "no_spring_onion": "No Spring Onion",
    "no_carrots": "No Carrots",
    "more_meat": "More Meat",
    "vegan": "Vegan",
    "add_bok_choy": "Add Bok Choy",
    "no_zucchini": "No Zucchini",
    "extra_cheese": "Extra Cheese",
    "no_egg": "No Egg",
    "extra_broth": "Extra Broth",
    "no_kimchi": "No Kimchi",
    "extra_tuna": "Extra Tuna",
    "less_rice": "Less Rice",
    "extra_kimchi": "Extra Kimchi",
    "no_cuccumber": "No Cuccumber"
}

MODE_NOTE_DEFAULTS: dict[str, list[str]] = {
    "R": ["less_spicy", "more_spicy", "no_mushroom"],
    "G": ["no_cuccumber"],
}

DISH_NOTE_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "pork_ramyun": {
        "add": ["more_more_spicy", "no_onions", "no_spring_onion", "no_carrots", "more_meat", "extra_broth"],
        "remove": [],
    },
    "chicken_ramyun": {
        "add": ["more_more_spicy", "no_onions", "no_spring_onion", "extra_broth"],
        "remove": ["more_meat"],
    },
    "original_ramyun": {
        "add": ["more_more_spicy", "no_onions", "no_spring_onion", "no_carrots", "more_meat", "extra_broth"],
        "remove": [],
    },
    "cheese_ramyun": {
        "add": ["less_less_spicy", "extra_cheese", "no_egg"],
        "remove": [],
    },
    "seafood_ramyun": {
        "add": ["less_less_spicy", "no_zucchini", "no_spring_onion"],
        "remove": ["more_meat"],
    },
    "kimchi_ramyun": {
        "add": ["vegan", "less_less_spicy", "no_kimchi", "extra_kimchi"],
        "remove": [],
    },
    "tofu_ramyun": {
        "add": ["vegan", "less_less_spicy", "add_bok_choy", "no_zucchini"],
        "remove": ["more_meat"],
    },
    "beef_gimbap": {
        "add": ["no_carrots", "no_onions", "more_meat"],
        "remove": [],
    },
    "tuna_gimbap": {
        "add": ["extra_tuna", "no_onions"],
        "remove": [],
    },
    "spicy_tuna_gimbap": {
        "add": ["extra_tuna", "less_spicy", "more_spicy", "no_onions"],
        "remove": [],
    },
    "sausage_gimbap": {
        "add": ["more_meat", "no_onions", "no_carrots"],
        "remove": [],
    },
    "mushroom_gimbap": {
        "add": ["no_onions", "no_carrots"],
        "remove": [],
    },
    "salad_gimbap": {
        "add": ["less_rice"],
        "remove": [],
    },
    "tteokbokki": {
        "add": ["less_spicy", "less_less_spicy", "more_spicy", "more_more_spicy", "extra_cheese", "no_onions"],
        "remove": [],
    },
    "tofu_gimbap": {
        "add": ["vegan"],
        "remove": [],
    },
}

DISH_META_BY_ID: dict[str, DishMeta] = {
    "beef_gimbap": DishMeta(display_name="Beef Gimbap", aliases=[]),
    "tuna_gimbap": DishMeta(display_name="Tuna Gimbap", aliases=[]),
    "spicy_tuna_gimbap": DishMeta(display_name="S-Tuna Gimbap", aliases=["st", "stuna", "s-tuna"]),
    "sausage_gimbap": DishMeta(display_name="Sausage Gimbap", aliases=[]),
    "mushroom_gimbap": DishMeta(display_name="Mushroom Gimbap", aliases=[]),
    "salad_gimbap": DishMeta(display_name="Salad Gimbap", aliases=[]),
    "tofu_gimbap": DishMeta(display_name="Tofu Gimbap", aliases=["tofu", "vegtofu"]),
    "pork_ramyun": DishMeta(display_name="Pork Ramyun", aliases=[]),
    "chicken_ramyun": DishMeta(display_name="Chicken Ramyun", aliases=["chix", "chicken"]),
    "original_ramyun": DishMeta(display_name="Original Ramyun", aliases=[]),
    "cheese_ramyun": DishMeta(display_name="Cheese Ramyun", aliases=["ches"]),
    "kimchi_ramyun": DishMeta(display_name="Kimchi Ramyun", aliases=[]),
    "seafood_ramyun": DishMeta(display_name="Seafood Ramyun", aliases=[], print_label="R-Sea"),
    "tofu_ramyun": DishMeta(display_name="Tofu Ramyun", aliases=["tofu", "vegtofu"]),
    "tteokbokki": DishMeta(display_name="Tteokbokki", aliases=[], print_label="T.T."),
    "kimchi_side": DishMeta(display_name="Kimchi", aliases=[]),
    "ssamjang_side": DishMeta(display_name="Ssamjang", aliases=[]),
    "namu_side": DishMeta(display_name="Namu", aliases=[]),
    "hot_side": DishMeta(display_name="Hot", aliases=[]),
    "rice_side": DishMeta(display_name="Rice", aliases=[]),
}


def display_name_for_dish(dish_id: str) -> str:
    """Get display name for a dish id."""
    meta = DISH_META_BY_ID.get(dish_id)
    if meta is None:
        return dish_id
    return meta.display_name


def print_label_override_for_dish(dish_id: str) -> str | None:
    """Get optional explicit print label for a dish id."""
    meta = DISH_META_BY_ID.get(dish_id)
    if meta is None:
        return None
    return meta.print_label


MENU_DISH_IDS_BY_MODE: dict[str, list[str]] = {
    "G": [
        "beef_gimbap",
        "tuna_gimbap",
        "spicy_tuna_gimbap",
        "sausage_gimbap",
        "mushroom_gimbap",
        "salad_gimbap",
        "tofu_gimbap",
    ],
    "R": [
        "pork_ramyun",
        "chicken_ramyun",
        "original_ramyun",
        "cheese_ramyun",
        "kimchi_ramyun",
        "seafood_ramyun",
        "tofu_ramyun",
    ],
    "S": [
        "kimchi_side",
        "ssamjang_side",
        "namu_side",
        "hot_side",
        "rice_side",
    ],
}

MENU_BY_MODE: dict[str, list[MenuItem]] = {
    mode: [MenuItem(dish_id, display_name_for_dish(dish_id)) for dish_id in dish_ids]
    for mode, dish_ids in MENU_DISH_IDS_BY_MODE.items()
}

# Compatibility export: derived from canonical dish metadata.
SEARCH_ALIASES_BY_DISH: dict[str, list[str]] = {
    dish_id: list(meta.aliases) for dish_id, meta in DISH_META_BY_ID.items() if meta.aliases
}
