import base64
import sys
import json
import mimetypes
from pathlib import Path
from typing import Any, Callable, Sequence

import flet as ft

# Kiểm tra xem ứng dụng đang chạy ở dạng file .exe hay script .py
if getattr(sys, 'frozen', False):
    # Nếu là file .exe, lấy thư mục chứa chính file .exe đó ở bên ngoài
    APP_DIR = Path(sys.executable).resolve().parent
else:
    # Nếu là file .py chạy bình thường khi code
    APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = APP_DIR / "config.json"
BACKGROUND_DIR = APP_DIR / "resources" / "Background"
MUSIC_DIR = APP_DIR / "resources" / "Music"
THEMES: dict[str, dict[str, str]] = {
    "midnight": {
        "label": "Xanh đêm",
        "background": "#151B2B",
        "surface": "#484A58FF",
        "text": "#000000",
        "muted": "#002E89",
        "border": "#111827",
    },
    "light": {
        "label": "Sáng",
        "background": "#F3F4F6",
        "surface": "#FFFFFF",
        "text": "#1F2937",
        "muted": "#4B5563",
        "border": "#D1D5DB",
    },
    "dark": {
        "label": "Tối",
        "background": "#111827",
        "surface": "#1F2937",
        "text": "#F9FAFB",
        "muted": "#D1D5DB",
        "border": "#374151",
    },
}

_BACKGROUND_OPACITY = {
    "midnight": 0.76,
    "light": 0.38,
    "dark": 0.52,
}


def style_dropdown_options(
    dropdowns: Sequence[ft.Dropdown],
    theme_name: str,
) -> None:
    palette = THEMES.get(theme_name)
    if palette is None:
        raise ValueError(f"Giao diện không hợp lệ: {theme_name}")
    for dropdown in dropdowns:
        for option in dropdown.options:
            option.style = ft.ButtonStyle(
                color=palette["text"],
                bgcolor=palette["surface"],
                text_style=ft.TextStyle(
                    color=palette["text"],
                    size=15,
                    weight=ft.FontWeight.W_500,
                ),
            )


_DEFAULTS: dict[str, Any] = {
    "download_url": "",
    "download_directory": "../downloads",
    "theme": "midnight",
    "background_image": "resources/Background/Background 1.jpg",
    "music_file": "resources/Music/Tek It (Sped Up) - Cafuné.mp3",
    "music_volume": 0.35,
    "music_repeat": False,
    "music_autoplay": True,
}


def load_preferences() -> dict[str, Any]:
    try:
        preferences = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _DEFAULTS.copy()
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Không thể đọc cấu hình {CONFIG_FILE}: {exc}") from exc
    if not isinstance(preferences, dict):
        raise ValueError("Tệp config.json phải chứa một đối tượng JSON.")

    result = {**_DEFAULTS, **preferences}
    if result["theme"] not in THEMES:
        raise ValueError("Giao diện trong config.json không hợp lệ.")
    volume = result["music_volume"]
    if (
        isinstance(volume, bool)
        or not isinstance(volume, (int, float))
        or not 0 <= volume <= 1
    ):
        raise ValueError("Âm lượng trong config.json phải nằm trong khoảng 0 đến 1.")
    for key in ("music_repeat", "music_autoplay"):
        if not isinstance(result[key], bool):
            raise ValueError(f"{key} trong config.json phải là true hoặc false.")
    for key in ("download_directory", "background_image", "music_file"):
        if result[key] is not None and not isinstance(result[key], str):
            raise ValueError(f"{key} trong config.json phải là chuỗi hoặc null.")
    return result


def save_preferences(**updates: Any) -> dict[str, Any]:
    preferences = load_preferences()
    preferences.update(updates)
    try:
        temporary_file = CONFIG_FILE.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps(preferences, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_file.replace(CONFIG_FILE)
    except OSError as exc:
        raise OSError(f"Không thể cập nhật cấu hình {CONFIG_FILE}: {exc}") from exc
    return preferences


def _resolve_configured_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = APP_DIR / resolved
    return resolved.resolve()


def get_download_directory() -> Path:
    configured = load_preferences()["download_directory"]
    if not configured:
        raise ValueError("Cần thiết lập download_directory trong config.json.")
    return _resolve_configured_path(configured)


def set_download_directory(directory: str | Path) -> Path:
    value = str(directory).strip()
    if not value:
        raise ValueError("Vui lòng nhập địa chỉ thư mục lưu file.")

    folder = _resolve_configured_path(value)
    folder.mkdir(parents=True, exist_ok=True)
    save_preferences(download_directory=str(folder))
    return folder


def get_background_options() -> list[tuple[str, str]]:
    if not BACKGROUND_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục ảnh nền: {BACKGROUND_DIR}")
    return [
        (path.relative_to(APP_DIR).as_posix(), path.stem)
        for path in sorted(BACKGROUND_DIR.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}
    ]


def get_music_options() -> list[tuple[str, str]]:
    if not MUSIC_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục nhạc: {MUSIC_DIR}")
    return [
        (path.relative_to(APP_DIR).as_posix(), path.name)
        for path in sorted(MUSIC_DIR.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and path.suffix.casefold() in {".mp3", ".wav", ".ogg", ".flac"}
    ]


def get_background_path(background: str | None = None) -> Path | None:
    configured = background or load_preferences()["background_image"]
    if not configured:
        return None
    path = _resolve_configured_path(configured)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh nền: {path}")
    return path


def get_background_source(background: str | None = None) -> str | None:
    path = get_background_path(background)
    if path is None:
        return None
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def get_music_path(music_file: str | None = None) -> Path | None:
    configured = music_file or load_preferences()["music_file"]
    if not configured:
        return None
    path = _resolve_configured_path(configured)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp nhạc: {path}")
    return path


def apply_theme(
    page: ft.Page,
    theme_name: str,
    *,
    surfaces: Sequence[ft.Container] = (),
    primary_texts: Sequence[ft.Control] = (),
    muted_texts: Sequence[ft.Control] = (),
    borders: Sequence[ft.Container] = (),
    icons: Sequence[ft.Icon] = (),
    dropdowns: Sequence[ft.Dropdown] = (),
    background_layer: ft.Container | None = None,
) -> None:
    palette = THEMES.get(theme_name)
    if palette is None:
        raise ValueError(f"Giao diện không hợp lệ: {theme_name}")

    page.bgcolor = palette["background"]
    for control in surfaces:
        control.bgcolor = palette["surface"]
    if background_layer is not None:
        background_layer.bgcolor = palette["background"]
        if background_layer.image is not None:
            background_layer.image = background_layer.image.copy(
                opacity=_BACKGROUND_OPACITY[theme_name]
            )
    for control in primary_texts:
        if isinstance(control, ft.TextField):
            control.text_style = ft.TextStyle(color=palette["text"], size=17)
            control.hint_style = ft.TextStyle(color=palette["muted"], size=17)
        elif isinstance(control, ft.Text):
            control.color = palette["text"]
    for control in muted_texts:
        if isinstance(control, ft.TextField):
            control.text_style = ft.TextStyle(color=palette["muted"], size=14)
            control.hint_style = ft.TextStyle(color=palette["muted"], size=14)
        elif isinstance(control, ft.Text):
            control.color = palette["muted"]
    for control in borders:
        control.border = ft.Border.all(2, palette["border"])
    for icon in icons:
        icon.color = palette["text"]
    for dropdown in dropdowns:
        dropdown.text_style = ft.TextStyle(color=palette["text"], size=16)
        dropdown.label_style = ft.TextStyle(color=palette["text"], size=14)
        dropdown.bgcolor = palette["surface"]
        dropdown.border_color = palette["border"]
        dropdown.focused_border_color = palette["text"]
    style_dropdown_options(dropdowns, theme_name)
    page.update()


def build_settings_dialog(
    page: ft.Page,
    music_controls: ft.Control,
    background_image: str,
    on_theme_change: Callable[[str], None],
    on_background_change: Callable[[str], None],
) -> ft.AlertDialog:
    preferences = load_preferences()
    theme_picker = ft.Dropdown(
        label="Màu giao diện",
        value=preferences["theme"],
        options=[
            ft.DropdownOption(key=name, text=theme["label"])
            for name, theme in THEMES.items()
        ],
        expand=True,
    )
    backgrounds = get_background_options()
    background_values = {path for path, _ in backgrounds}
    current_background = background_image
    if current_background not in background_values:
        try:
            current_background = _resolve_configured_path(background_image).relative_to(
                APP_DIR
            ).as_posix()
        except ValueError:
            current_background = ""
    if current_background not in background_values:
        current_background = backgrounds[0][0] if backgrounds else None
    background_picker = ft.Dropdown(
        label="Ảnh nền",
        value=current_background,
        options=[
            ft.DropdownOption(key=path, text=label)
            for path, label in backgrounds
        ],
        expand=True,
    )
    feedback = ft.Text("", size=12, color="#DC2626")

    def change_theme(event: ft.ControlEvent) -> None:
        theme_name = event.control.value
        if not theme_name:
            return
        try:
            save_preferences(theme=theme_name)
            on_theme_change(theme_name)
            feedback.value = ""
        except (OSError, ValueError) as exc:
            feedback.value = f"Không thể lưu giao diện: {exc}"
            page.update()

    def change_background(event: ft.ControlEvent) -> None:
        selected_background = event.control.value
        if not selected_background:
            return
        try:
            on_background_change(selected_background)
            feedback.value = ""
        except (OSError, ValueError) as exc:
            feedback.value = f"Không thể đổi ảnh nền: {exc}"
            page.update()

    theme_picker.on_select = change_theme
    background_picker.on_select = change_background
    return ft.AlertDialog(
        modal=True,
        title=ft.Text("Cài đặt"),
        content=ft.Column(
            [
                theme_picker,
                background_picker,
                feedback,
                ft.Divider(height=1),
                ft.Text("Nhạc nền", size=17, weight=ft.FontWeight.BOLD),
                music_controls,
            ],
            tight=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            width=520,
        ),
        actions=[
            ft.TextButton("Đóng", on_click=lambda _: page.pop_dialog()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
