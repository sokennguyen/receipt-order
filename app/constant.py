"""Editable static menu and note configuration."""

from __future__ import annotations

NOTE_CATALOG: dict[str, str] = {
    "less_spicy": "Less Spicy",
    "less_less_spicy": "Less Less Spicy",
    "more_spicy": "More Spicy",
    "more_more_spicy": "More More Spicy",
    "no_mushroom": "No Mush",
    "no_onions": "No Onions",
    "more_cheese": "More Cheese",
    "more_cream": "More Cream",
    "no_spring_onion": "No Spring",
    "no_carrots": "No Carrots",
    "more_meat": "More Meat",
    "vegan": "Vegan",
    "more_veggies": "More Veg",
    "add_pok_choi": "Add pok choi",
    "no_zucchini": "No Zucc",
    "more_zucchini": "More Zucc",
    "add_cheese": "Add Cheese",
    "no_egg": "No Egg",
    "less_rice": "Less Rice",
    "no_cuccumber": "No Cuccumber",
    "no_spinach": "No Spinach",
    "no_pepper": "No Pepper",
    "no_squid": "No Squid",
    "no_octopus": "No Octopus",
    "no_clams": "No Clams"
}

MODE_NOTE_DEFAULTS: dict[str, list[str]] = {
    "R": ["less_spicy", "less_less_spicy", "more_spicy", "more_more_spicy", "no_spring_onion", "no_mushroom", "add_cheese"],
    "G": ["no_cuccumber", "no_carrots", "no_spinach"],
}

DISH_NOTE_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "pork_ramyun": {
        "add": ["no_onions", "no_carrots", "more_meat"],
        "remove": [],
    },
    "chicken_ramyun": {
        "add": ["no_pepper", "more_meat"],
        "remove": [],
    },
    "original_ramyun": {
        "add": [],
        "remove": [],
    },
    "cheese_ramyun": {
        "add": ["vegan"],
        "remove": [],
    },
    "seafood_ramyun": {
        "add": ["no_squid", "no_octopus", "no_clams"],
        "remove": [],
    },
    "kimchi_ramyun": {
        "add": ["vegan"],
        "remove": [],
    },
    "tofu_ramyun": {
        "add": ["vegan", "add_pok_choi", "no_zucchini", "more_zucchini", "more_veggies"],
        "remove": [],
    },
    "beef_gimbap": {
        "add": ["no_carrots", "no_onions", "more_meat"],
        "remove": [],
    },
    "tuna_gimbap": {
        "add": ["no_onions"],
        "remove": [],
    },
    "spicy_tuna_gimbap": {
        "add": ["less_spicy", "more_spicy", "no_onions"],
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
        "add": [],
        "remove": [],
    },
    "tteokbokki": {
        "add": ["more_cream", "more_cheese", "no_spring_onion"],
        "remove": [],
    },
    "tofu_gimbap": {
        "add": [],
        "remove": [],
    },
}

# Canonical dish metadata values consumed by app.data (which wraps these into DishMeta dataclass instances).
DISH_META_BY_ID: dict[str, dict[str, str | list[str] | None]] = {
    "beef_gimbap": {"display_name": "Beef Gimbap", "aliases": ["bf","bef","bfe"], "print_label": None},
    "tuna_gimbap": {"display_name": "Tuna Gimbap", "aliases": [], "print_label": None},
    "spicy_tuna_gimbap": {"display_name": "S.Tuna Gimbap", "aliases": ["st", "stuna", "s-tuna"], "print_label": "G-S.T."},
    "sausage_gimbap": {"display_name": "Sausage Gimbap", "aliases": [], "print_label": "G-Saus"},
    "mushroom_gimbap": {"display_name": "Mushroom Gimbap", "aliases": [], "print_label": "G-Mush"},
    "salad_gimbap": {"display_name": "Salad Gimbap", "aliases": ["sl"], "print_label": None},
    "tofu_gimbap": {"display_name": "Tofu Gimbap", "aliases": ["tofu", "tf"], "print_label": None},
    "pork_ramyun": {"display_name": "Pork Ramyun", "aliases": [], "print_label": None},
    "chicken_ramyun": {"display_name": "Chicken Ramyun", "aliases": ["chix", "chicken", "ci"], "print_label": "R-Chix"},
    "original_ramyun": {"display_name": "Original Ramyun", "aliases": [], "print_label": "R-Origi"},
    "cheese_ramyun": {"display_name": "Cheese Ramyun", "aliases": ["ches"], "print_label": None},
    "kimchi_ramyun": {"display_name": "Kimchi Ramyun", "aliases": [], "print_label": None},
    "seafood_ramyun": {"display_name": "Seafood Ramyun", "aliases": ["sae"], "print_label": "R-Sea"},
    "tofu_ramyun": {"display_name": "Tofu Ramyun", "aliases": ["tofu", "tf"], "print_label": None},
    "tteokbokki": {"display_name": "Tteokbokki", "aliases": [], "print_label": "T.T."},
    "kimchi_side": {"display_name": "Kimchi", "aliases": [], "print_label": None},
    "ssamjang_side": {"display_name": "Ssamjang", "aliases": [], "print_label": "Ssam"},
    "namu_side": {"display_name": "Namu", "aliases": [], "print_label": None},
    "hot_side": {"display_name": "Hot", "aliases": [], "print_label": None},
    "rice_side": {"display_name": "Rice", "aliases": [], "print_label": None},
    "chili_side": {"display_name": "Extra chili aside", "aliases": ["chil"], "print_label": "Chili side"},
    "hot_water_side": {"display_name": "Hot water", "aliases": ["wt"], "print_label": "hot water"},
    "other_side": {"display_name": "Other item", "aliases": ["other"], "print_label": None},
}

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
        "chili_side",
        "hot_water_side",
        "other_side",
    ],
}

NOTE_PRINT_SPICY_SYMBOL_OVERRIDES: dict[str, str] = {
    "less_spicy": "☆",
    "less_less_spicy": "☆☆",
    "more_spicy": "♥",
    "more_more_spicy": "♥♥",
}

NOTE_PRINT_PREFIX_TO_SYMBOL_BY_ID: dict[str, str] = {
    "no_": "x",
    "less_": "-",
    "more_": "+",
    "add_": "^",
}

NOTE_PRINT_PREFIX_TO_SYMBOL_BY_TEXT: dict[str, str] = {
    "no": "x",
    "less": "-",
    "more": "+",
    "add": "^",
}
