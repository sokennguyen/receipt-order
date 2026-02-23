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
}

MODE_NOTE_DEFAULTS: dict[str, list[str]] = {
    "R": ["less_spicy", "more_spicy", "no_mushroom"],
    "G": ["less_rice"],
}

DISH_NOTE_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "classic_ramyun": {
        "add": ["more_more_spicy", "no_onions", "no_spring_onion", "no_carrots", "more_meat", "extra_broth"],
        "remove": [],
    },
    "shin_ramyun": {
        "add": ["more_more_spicy", "no_onions", "no_spring_onion", "extra_broth"],
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
        "add": ["less_less_spicy", "no_kimchi", "extra_kimchi"],
        "remove": [],
    },
    "pork_gimbap": {
        "add": ["no_carrots", "no_onions", "more_meat"],
        "remove": [],
    },
    "tuna_mayo_gimbap": {
        "add": ["extra_tuna", "no_onions"],
        "remove": [],
    },
    "cheese_gimbap": {
        "add": ["extra_cheese", "no_carrots"],
        "remove": [],
    },
    "bulgogi_gimbap": {
        "add": ["more_meat", "no_onions", "no_carrots"],
        "remove": [],
    },
    "kimchi_gimbap": {
        "add": ["extra_kimchi", "no_kimchi"],
        "remove": [],
    },
    "tteokbokki": {
        "add": ["less_spicy", "less_less_spicy", "more_spicy", "more_more_spicy", "extra_cheese", "no_onions"],
        "remove": [],
    },
}

MENU_BY_MODE: dict[str, list[MenuItem]] = {
    "G": [
        MenuItem("pork_gimbap", "Pork Gimbap"),
        MenuItem("tuna_mayo_gimbap", "Tuna Mayo Gimbap"),
        MenuItem("cheese_gimbap", "Cheese Gimbap"),
        MenuItem("bulgogi_gimbap", "Bulgogi Gimbap"),
        MenuItem("kimchi_gimbap", "Kimchi Gimbap"),
    ],
    "R": [
        MenuItem("classic_ramyun", "Classic Ramyun"),
        MenuItem("shin_ramyun", "Shin Ramyun"),
        MenuItem("cheese_ramyun", "Cheese Ramyun"),
        MenuItem("seafood_ramyun", "Seafood Ramyun"),
        MenuItem("kimchi_ramyun", "Kimchi Ramyun"),
    ],
}
