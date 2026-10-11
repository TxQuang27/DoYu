import asyncio

import flet as ft
from yt_dlp.utils import DownloadError

from UI.music import BackgroundMusic
from UI.settings import (
    THEMES,
    apply_theme,
    build_settings_dialog,
    get_background_source,
    get_download_directory,
    get_music_options,
    get_music_path,
    load_preferences,
    save_preferences,
    set_download_directory,
)
from downloader import (
    download_audio,
    download_video,
    get_download_folder,
    get_video_data,
)


# ============================================================
# DoYu_Flet - UI/Home
# Giao diện tìm kiếm và tải video/audio.
# ============================================================

BG_COLOR = "#151B2B"
PANEL_COLOR = "#FFFFFF"
TEXT_COLOR = "#060000"
MUTED_COLOR = "#0054FC"
BORDER_COLOR = "#111827"
GREEN_COLOR = "#16A34A"
RED_COLOR = "#DC2626"


def main(page: ft.Page):
    preferences = load_preferences()
    active_theme = preferences.get("theme", "midnight")
    page.title = "DoYu"
    page.bgcolor = THEMES[active_theme]["background"]
    page.padding = 0
    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    music_player = BackgroundMusic()

    # --------------------------------------------------------
    # Trạng thái UI
    # --------------------------------------------------------
    url_input = ft.TextField(
        hint_text="Nhập link bạn muốn tải",
        hint_style=ft.TextStyle(color="#777777", size=17),
        text_style=ft.TextStyle(color=TEXT_COLOR, size=17),
        border=ft.InputBorder.NONE,
        expand=True,
        content_padding=ft.Padding(left=20, top=14, right=20, bottom=14,),
        border_radius = 10,
        on_submit=lambda e: search_video(e),
    )

    status_text = ft.Text(
        "",
        color=MUTED_COLOR,
        size=14,
        visible=False,
    )

    thumbnail_placeholder = ft.Column(
        [
            ft.Icon(
                ft.Icons.IMAGE_OUTLINED,
                size=42,
                color="#9CA3AF",
            ),
            ft.Text(
                "Không có thumbnail",
                color="#100105",
                size=14,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4,
    )
    thumbnail = ft.Container(
        width=280,
        height=180,
        bgcolor="#E5E7EB",
        border_radius=18,
        alignment=ft.Alignment.CENTER,
        content=thumbnail_placeholder,
    )
    thumbnail_view = ft.Container(
        content=thumbnail,
        margin=ft.Margin.only(top=28),
        alignment=ft.Alignment.CENTER_LEFT,
    )

    video_title = ft.Text(
        "Tên video",
        size=20,
        weight=ft.FontWeight.BOLD,
        color="#111827",
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    author_text = ft.Text(
        "Tác giả",
        size=16,
        weight=ft.FontWeight.W_500,
        color="#374151",
    )

    duration_text = ft.Text(
        "Thời lượng: --:--",
        size=16,
        weight=ft.FontWeight.W_500,
        color="#374151",
    )
    author_icon = ft.Icon(ft.Icons.PERSON_OUTLINE, size=20, color="#374151")
    duration_icon = ft.Icon(ft.Icons.SCHEDULE_OUTLINED, size=20, color="#374151")

    video_quality = ft.Dropdown(
        label="Chất lượng video",
        options=[],
        expand=True,
        disabled=True,
        text_size=16,
        text_style=ft.TextStyle(color=TEXT_COLOR, size=16),
        label_style=ft.TextStyle(color=TEXT_COLOR, size=14),
        border_color="#F70000",
        focused_border_color="#1D4ED8",
    )
    audio_quality = ft.Dropdown(
        label="Chất lượng âm thanh",
        options=[],
        expand=True,
        disabled=True,
        text_size=16,
        text_style=ft.TextStyle(color=TEXT_COLOR, size=16),
        label_style=ft.TextStyle(color=TEXT_COLOR, size=14),
        border_color="#F70000",
        focused_border_color="#1D4ED8",
    )

    # --------------------------------------------------------
    # Download buttons
    # --------------------------------------------------------
    async def download_mp4(e):
        url = (url_input.value or "").strip()
        if not url or not result_card.visible:
            set_status("Hãy tìm video trước khi tải.", RED_COLOR)
            return

        mp4_button.disabled = True
        set_status("Đang tải video...")
        try:
            await asyncio.to_thread(download_video, url, video_quality.value)
        except (DownloadError, OSError, ValueError) as exc:
            set_status(f"Không thể tải video: {exc}", RED_COLOR)
        else:
            set_status(f"Tải video hoàn tất. Thư mục: {get_download_folder()}", GREEN_COLOR)
        finally:
            mp4_button.disabled = False
            page.update()

    async def download_mp3(e):
        url = (url_input.value or "").strip()
        if not url or not result_card.visible:
            set_status("Hãy tìm video trước khi tải.", RED_COLOR)
            return

        mp3_button.disabled = True
        set_status("Đang chuyển đổi và tải MP3...")
        try:
            await asyncio.to_thread(download_audio, url, audio_quality.value)
        except (DownloadError, OSError, ValueError) as exc:
            set_status(f"Không thể tải âm thanh: {exc}", RED_COLOR)
        else:
            set_status(f"Tải MP3 hoàn tất. Thư mục: {get_download_folder()}", GREEN_COLOR)
        finally:
            mp3_button.disabled = False
            page.update()

    mp4_icon = ft.Icon(
        ft.Icons.VIDEO_FILE_OUTLINED,
        size=34,
        color=TEXT_COLOR,
    )
    mp4_title = ft.Text(
        "MP4",
        size=17,
        weight=ft.FontWeight.BOLD,
        color=TEXT_COLOR,
    )
    mp4_subtitle = ft.Text("Video", size=12, color=MUTED_COLOR)
    mp4_button = ft.Container(
        width=145,
        height=115,
        border=ft.Border.all(2, BORDER_COLOR),
        border_radius=12,
        bgcolor="#FFFFFF",
        ink=True,
        alignment=ft.Alignment.CENTER,
        on_click=download_mp4,
        content=ft.Column(
            [
                mp4_icon,
                mp4_title,
                mp4_subtitle,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=3,
        ),
    )

    mp3_icon = ft.Icon(
        ft.Icons.AUDIO_FILE_OUTLINED,
        size=34,
        color=TEXT_COLOR,
    )
    mp3_title = ft.Text(
        "MP3",
        size=17,
        weight=ft.FontWeight.BOLD,
        color=TEXT_COLOR,
    )
    mp3_subtitle = ft.Text("Audio", size=12, color=MUTED_COLOR)
    mp3_button = ft.Container(
        width=145,
        height=115,
        border=ft.Border.all(2, BORDER_COLOR),
        border_radius=12,
        bgcolor="#FFFFFF",
        ink=True,
        alignment=ft.Alignment.CENTER,
        on_click=download_mp3,
        content=ft.Column(
            [
                mp3_icon,
                mp3_title,
                mp3_subtitle,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=3,
        ),
    )

    # --------------------------------------------------------
    # Khu vực kết quả
    # --------------------------------------------------------
    result_info = ft.Column(
        [
            video_title,
            ft.Row(
                [
                    author_icon,
                    author_text,
                ],
                spacing=8,
            ),
            ft.Row(
                [
                    duration_icon,
                    duration_text,
                ],
                spacing=8,
            ),
        ],
        spacing=12,
        expand=True,
    )

    result_card = ft.Container(
        visible=False,
        padding=24,
        border=ft.Border.all(1, "#E5E7EB"),
        border_radius=16,
        bgcolor=PANEL_COLOR,
        content=ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            thumbnail_view,
                            col={"sm": 12, "md": 3, "lg": 3},
                        ),
                        ft.Container(
                            result_info,
                            col={"sm": 12, "md": 5, "lg": 5},
                            padding=ft.Padding.only(left=12, right=12),
                        ),
                        ft.Container(
                            ft.Row(
                                [mp4_button, mp3_button],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                                wrap=True,
                            ),
                            col={"sm": 12, "md": 4, "lg": 4},
                            alignment=ft.Alignment.CENTER,
                        ),
                    ],
                    spacing=0,
                    run_spacing=18,
                ),
                ft.Divider(height=1, color="#E5E7EB"),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            video_quality,
                            col={"sm": 12, "md": 6, "lg": 6},
                        ),
                        ft.Container(
                            audio_quality,
                            col={"sm": 12, "md": 6, "lg": 6},
                        ),
                    ],
                    spacing=16,
                    run_spacing=10,
                ),
            ],
            spacing=16,
        ),
    )

    # --------------------------------------------------------
    # Hàm xử lý tìm kiếm
    # --------------------------------------------------------
    def set_status(message, color=MUTED_COLOR):
        status_text.value = message
        status_text.color = color
        status_text.visible = True
        page.update()

    def format_duration(duration):
        if not isinstance(duration, (int, float)):
            return "--:--"
        total_seconds = int(duration)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    async def search_video(e):
        url = (url_input.value or "").strip()

        if not url:
            result_card.visible = False
            set_status("Vui lòng nhập link video trước.", RED_COLOR)
            return

        result_card.visible = False
        video_quality.options = []
        video_quality.value = None
        video_quality.disabled = True
        audio_quality.options = []
        audio_quality.value = None
        audio_quality.disabled = True
        search_button.disabled = True
        set_status("Đang lấy thông tin video...")
        try:
            video_data = await asyncio.to_thread(get_video_data, url)
        except (DownloadError, OSError, ValueError) as exc:
            set_status(f"Không thể lấy thông tin video: {exc}", RED_COLOR)
        else:
            metadata = video_data["metadata"]
            video_title.value = metadata.get("title") or "Không rõ tên video"
            author_text.value = f"Kênh: {metadata.get('author') or 'Không rõ'}"
            duration_text.value = f"Thời lượng: {format_duration(metadata.get('duration'))}"

            thumbnail_url = metadata.get("thumbnail")
            if thumbnail_url:
                thumbnail.content = ft.Image(
                    src=thumbnail_url,
                    width=280,
                    height=180,
                    fit=ft.BoxFit.COVER,
                    border_radius=18,
                )
            else:
                thumbnail.content = thumbnail_placeholder

            video_options = video_data["video_formats"]
            video_quality.options = [
                ft.DropdownOption(key=format_id, text=label)
                for format_id, label in video_options
            ]
            if video_options:
                video_quality.value = video_options[0][0]
                video_quality.disabled = False

            audio_options = video_data["audio_formats"]
            audio_quality.options = [
                ft.DropdownOption(key=format_id, text=label)
                for format_id, label in audio_options
            ]
            if audio_options:
                audio_quality.value = audio_options[0][0]
                audio_quality.disabled = False

            result_card.visible = True
            set_status("Đã tải thông tin video.", GREEN_COLOR)
        finally:
            search_button.disabled = False
            page.update()

    # --------------------------------------------------------
    # Search bar
    # --------------------------------------------------------
    search_button_text = ft.Text(
        "Tìm kiếm",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=TEXT_COLOR,
    )
    search_button = ft.Container(
        width=115,
        height=58,
        border=ft.Border.only(
    left=ft.BorderSide(2, BORDER_COLOR)
),
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=search_video,
        content=search_button_text,
    )

    search_bar = ft.Container(
        expand=True,
        height=60,
        bgcolor="#FFFFFF",
        border=ft.Border.all(1, BORDER_COLOR),
        border_radius=18,
        content=ft.Row(
            [
                url_input,
                search_button,
            ],
            spacing=0,
        ),
    )

    download_directory_field = ft.TextField(
        label="Thư mục lưu file",
        value=str(get_download_directory()),
        hint_text="Nhập đường dẫn thư mục",
        expand=True,
        on_submit=lambda _: save_download_directory(),
    )
    download_directory_status = ft.Text("", size=12, color=MUTED_COLOR)

    async def choose_download_directory(_: ft.ControlEvent) -> None:
        try:
            selected_directory = await file_picker.get_directory_path(
                dialog_title="Chọn thư mục lưu file",
                initial_directory=download_directory_field.value,
            )
            if selected_directory:
                download_directory_field.value = selected_directory
                save_download_directory()
        except (OSError, ValueError) as exc:
            download_directory_status.value = f"Không thể chọn thư mục: {exc}"
            download_directory_status.color = RED_COLOR
            page.update()

    def save_download_directory() -> None:
        try:
            folder = set_download_directory(download_directory_field.value or "")
        except (OSError, ValueError) as exc:
            download_directory_status.value = f"Không thể lưu thư mục: {exc}"
            download_directory_status.color = RED_COLOR
        else:
            download_directory_field.value = str(folder)
            download_directory_status.value = "Đã lưu thư mục tải."
            download_directory_status.color = GREEN_COLOR
        page.update()

    def choose_music_track(_: ft.ControlEvent) -> None:
        try:
            music_options = get_music_options()
            if not music_options:
                raise FileNotFoundError("Không có tệp nhạc trong resources/Music.")
            current_music = preferences.get("music_file")
            current_music_path = get_music_path(current_music) if current_music else None
            selected_music = next(
                (
                    relative_path
                    for relative_path, _ in music_options
                    if current_music_path
                    and get_music_path(relative_path) == current_music_path
                ),
                music_options[0][0],
            )
            music_picker = ft.Dropdown(
                label="Chọn nhạc nền",
                value=selected_music,
                options=[
                    ft.DropdownOption(key=path, text=label)
                    for path, label in music_options
                ],
                expand=True,
            )

            def confirm_music_selection(_: ft.ControlEvent) -> None:
                selected_music = music_picker.value
                if not selected_music:
                    return
                try:
                    selected_path = get_music_path(selected_music)
                    if selected_path is None:
                        raise ValueError("Hãy chọn tệp nhạc nền.")
                    music_player.select_track(selected_path)
                    preferences["music_file"] = selected_music
                    music_player.update_track_controls(selected_path)
                    page.pop_dialog()
                    page.update()
                except (OSError, ValueError) as exc:
                    set_status(f"Không thể mở nhạc nền: {exc}", RED_COLOR)

            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Chọn nhạc nền"),
                    content=music_picker,
                    actions=[
                        ft.TextButton("Hủy", on_click=lambda _: page.pop_dialog()),
                        ft.TextButton("Chọn", on_click=confirm_music_selection),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
            )
        except (OSError, ValueError) as exc:
            set_status(f"Không thể mở nhạc nền: {exc}", RED_COLOR)

    music_controls = music_player.build_controls(page, choose_music_track)

    settings_icon = ft.Icon(ft.Icons.SETTINGS_OUTLINED)
    settings_button = ft.IconButton(
        icon=settings_icon,
        tooltip="Cài đặt giao diện và nhạc nền",
        on_click=lambda _: page.show_dialog(settings_dialog),
    )
    theme_surfaces = [
        search_bar,
        search_button,
        result_card,
        mp4_button,
        mp3_button,
        thumbnail,
    ]
    theme_primary_texts = [
        url_input,
        video_title,
        search_button_text,
        mp4_title,
        mp3_title,
        download_directory_field,
    ]
    theme_muted_texts = [
        author_text,
        duration_text,
        mp4_subtitle,
        mp3_subtitle,
        thumbnail_placeholder.controls[1],
        status_text,
    ]
    theme_borders = [result_card, mp4_button, mp3_button]
    theme_icons = [
        author_icon,
        duration_icon,
        mp4_icon,
        mp3_icon,
        thumbnail_placeholder.controls[0],
        settings_icon,
    ]

    def change_theme(theme_name: str) -> None:
        apply_theme(
            page,
            theme_name,
            surfaces=theme_surfaces,
            primary_texts=theme_primary_texts,
            muted_texts=theme_muted_texts,
            borders=theme_borders,
            icons=theme_icons,
            dropdowns=[video_quality, audio_quality],
            background_layer=background_layer,
        )

    def change_background(background_file: str) -> None:
        background_source = get_background_source(background_file)
        if background_source is None:
            raise ValueError("Hãy chọn một ảnh nền.")
        save_preferences(background_image=background_file)
        background_layer.image = ft.DecorationImage(
            src=background_source,
            fit=ft.BoxFit.COVER,
            opacity=(
                background_layer.image.opacity
                if background_layer.image is not None
                else 0.76
            ),
        )
        page.update()

    settings_dialog = build_settings_dialog(
        page,
        music_controls,
        preferences["background_image"],
        change_theme,
        change_background,
    )
    download_directory_row = ft.Row(
        [
            download_directory_field,
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                tooltip="Chọn thư mục tải",
                on_click=choose_download_directory,
            ),
            ft.IconButton(
                icon=ft.Icons.CHECK,
                tooltip="Lưu địa chỉ thư mục",
                on_click=lambda _: save_download_directory(),
            ),
        ],
        spacing=4,
    )

    # --------------------------------------------------------
    # Main layout
    # --------------------------------------------------------
    content = ft.Column(
        [
            ft.Container(
                height=55,
            ),

            # Search
            ft.Row(
                [search_bar, settings_button],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),

            ft.Container(height=12),
            ft.Container(
                content=ft.Column(
                    [download_directory_row, download_directory_status],
                    spacing=2,
                ),
                width=900,
                padding=ft.Padding.only(left=16, right=16),
            ),

            ft.Container(height=23),

            # Result panel
            ft.Container(
                content=ft.Column(
                    [
                        result_card,
                        status_text,
                    ],
                    spacing=10,
                ),
                expand=True,
                padding=ft.Padding.only(left=16, right=16),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    initial_background = get_background_source(preferences["background_image"])
    background_layer = ft.Container(
        content=content,
        image=(
            ft.DecorationImage(
                src=initial_background,
                fit=ft.BoxFit.COVER,
                opacity=0.76,
            )
            if initial_background
            else None
        ),
        expand=True,
    )

    page.add(background_layer)
    change_theme(active_theme)
    if preferences.get("music_autoplay") and music_player.file_path:
        try:
            music_player.play()
        except (OSError, ValueError) as exc:
            set_status(f"Không thể phát nhạc nền: {exc}", RED_COLOR)
