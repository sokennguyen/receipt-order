"""Static menu and note data."""

from __future__ import annotations

from app.models import MenuItem

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

MENU_BY_MODE: dict[str, list[MenuItem]] = {
    "G": [
        MenuItem("beef_gimbap", "Beef Gimbap"),
        MenuItem("tuna_gimbap", "Tuna Gimbap"),
        MenuItem("spicy_tuna_gimbap", "S-Tuna Gimbap"),
        MenuItem("sausage_gimbap", "Sausage Gimbap"),
        MenuItem("mushroom_gimbap", "Mushroom Gimbap"),
        MenuItem("salad_gimbap", "Salad Gimbap"),
        MenuItem("tofu_gimbap", "Tofu Gimbap"),
    ],
    "R": [
        MenuItem("pork_ramyun", "Pork Ramyun"),
        MenuItem("chicken_ramyun", "Chicken Ramyun"),
        MenuItem("original_ramyun", "Original Ramyun"),
        MenuItem("cheese_ramyun", "Cheese Ramyun"),
        MenuItem("kimchi_ramyun", "Kimchi Ramyun"),
        MenuItem("seafood_ramyun", "Seafood Ramyun"),
        MenuItem("tofu_ramyun", "Tofu Ramyun"),
    ],
}
