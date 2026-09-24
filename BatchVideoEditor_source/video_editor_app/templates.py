"""Quản lý các mẫu (template) chỉnh sửa video, lưu trong templates.json"""
import json
import os

TEMPLATES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates.json")

DEFAULT_TEMPLATE = {
    "trim_start": 0,
    "trim_end": 0,
    "watermark": {"enabled": False, "path": "", "position": "bottom-right", "opacity": 0.7, "scale": 0.15},
    "intro": {"enabled": False, "path": ""},
    "outro": {"enabled": False, "path": ""},
    "bg_music": {"enabled": False, "path": "", "volume": 0.2},
    "subtitle": {"enabled": False, "font_size": 42, "color": "white", "position": "bottom"},
    "effects": {"fade_in_out": True, "zoom_ken_burns": False, "speed": 1.0},
}


def load_templates() -> dict:
    if not os.path.exists(TEMPLATES_FILE):
        save_templates({"Mặc định (không chỉnh)": DEFAULT_TEMPLATE})
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(templates: dict):
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def upsert_template(name: str, config: dict):
    templates = load_templates()
    templates[name] = config
    save_templates(templates)


def delete_template(name: str):
    templates = load_templates()
    if name in templates:
        del templates[name]
        save_templates(templates)


def new_blank_template() -> dict:
    return json.loads(json.dumps(DEFAULT_TEMPLATE))
