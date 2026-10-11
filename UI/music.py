import asyncio
import math
from pathlib import Path
from typing import Callable

import flet as ft
import pygame
from mutagen import File as MutagenFile, MutagenError

from UI.settings import (
    APP_DIR,
    get_music_options,
    get_music_path,
    load_preferences,
    save_preferences,
)


class BackgroundMusic:
    def __init__(self) -> None:
        preferences = load_preferences()
        configured_file = preferences.get("music_file")
        self.file_path = get_music_path(configured_file)
        self.playlist = [
            path
            for relative_path, _ in get_music_options()
            if (path := get_music_path(relative_path)) is not None
        ]
        if self.file_path and self.file_path not in self.playlist:
            self.playlist.append(self.file_path)
        self._track_index = (
            self.playlist.index(self.file_path)
            if self.file_path in self.playlist
            else None
        )
        self.volume = float(preferences["music_volume"])
        self.repeat = bool(preferences["music_repeat"])
        self.duration = 0.0
        self._mixer_ready = False
        self._loaded = False
        self._paused = False
        self._stopped = True
        self._start_offset = 0.0
        self._track_label: ft.Text | None = None
        self._progress_slider: ft.Slider | None = None
        self._progress_label: ft.Text | None = None
        self._playback_button: ft.IconButton | None = None

    def _initialize_mixer(self) -> None:
        if not self._mixer_ready:
            pygame.mixer.init()
            self._mixer_ready = True

    def select_track(self, file_path: str | Path) -> None:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Không tìm thấy tệp nhạc: {path}")

        try:
            track_info = MutagenFile(path)
        except (OSError, MutagenError) as exc:
            raise ValueError(f"Không thể đọc thông tin tệp nhạc: {exc}") from exc
        duration = getattr(getattr(track_info, "info", None), "length", None)
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Không đọc được thời lượng của tệp nhạc này.")

        try:
            self._initialize_mixer()
            pygame.mixer.music.load(str(path))
        except pygame.error as exc:
            raise ValueError(f"Không thể khởi tạo trình phát nhạc: {exc}") from exc

        self.file_path = path
        if path not in self.playlist:
            self.playlist.append(path)
        self._track_index = self.playlist.index(path)
        self.duration = float(duration)
        self._loaded = True
        self._paused = False
        self._stopped = True
        self._start_offset = 0.0
        try:
            saved_path = path.relative_to(APP_DIR).as_posix()
        except ValueError:
            saved_path = str(path)
        save_preferences(music_file=saved_path)

    def play(self) -> None:
        if not self._loaded and self.file_path:
            self.select_track(self.file_path)
        if not self._loaded:
            raise ValueError("Hãy chọn tệp nhạc nền trước.")
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False
            return
        self._start(self._start_offset)

    def pause(self) -> None:
        if self._loaded and pygame.mixer.music.get_busy():
            self._start_offset = self.position()
            pygame.mixer.music.pause()
            self._paused = True

    def stop(self) -> None:
        if self._loaded:
            pygame.mixer.music.stop()
        self._paused = False
        self._stopped = True
        self._start_offset = 0.0

    def next_track(self, *, automatic: bool = False) -> bool:
        if not self.playlist:
            raise ValueError("Không có bài nhạc nào trong resources/Music.")
        current_index = self._track_index if self._track_index is not None else -1
        next_index = current_index + 1
        if next_index >= len(self.playlist):
            if automatic:
                self.stop()
                return False
            next_index = 0
        self.select_track(self.playlist[next_index])
        self.play()
        return True

    def previous_track(self) -> None:
        if not self.playlist:
            raise ValueError("Không có bài nhạc nào trong resources/Music.")
        if self.position() > 3:
            self.seek(0)
            if self._stopped:
                self.play()
            return
        current_index = self._track_index if self._track_index is not None else 0
        previous_index = (current_index - 1) % len(self.playlist)
        self.select_track(self.playlist[previous_index])
        self.play()

    def seek(self, position: float) -> None:
        if not self._loaded:
            raise ValueError("Hãy chọn tệp nhạc nền trước.")

        position = min(max(float(position), 0.0), self.duration)
        was_paused = self._paused
        was_playing = pygame.mixer.music.get_busy() or was_paused
        if was_playing:
            self._start(position)
            if was_paused:
                pygame.mixer.music.pause()
                self._paused = True
        else:
            self._start_offset = position
            self._stopped = True

    def set_volume(self, volume: float, *, persist: bool = False) -> None:
        self.volume = min(max(float(volume), 0.0), 1.0)
        if self._mixer_ready:
            pygame.mixer.music.set_volume(self.volume)
        if persist:
            save_preferences(music_volume=self.volume)

    def set_repeat(self, repeat: bool) -> None:
        repeat = bool(repeat)
        if repeat == self.repeat:
            return
        self.repeat = repeat
        save_preferences(music_repeat=self.repeat)

        if self._loaded and (pygame.mixer.music.get_busy() or self._paused):
            was_paused = self._paused
            self._start(self.position())
            if was_paused:
                pygame.mixer.music.pause()
                self._paused = True

    def position(self) -> float:
        if not self._loaded:
            return 0.0
        if self._paused or self._stopped or not pygame.mixer.music.get_busy():
            return self._start_offset

        elapsed = max(pygame.mixer.music.get_pos(), 0) / 1000
        position = min(self._start_offset + elapsed, self.duration)
        if self.repeat and self.duration:
            position %= self.duration
        return position

    def _start(self, position: float) -> None:
        try:
            self._initialize_mixer()
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(
                loops=-1 if self.repeat else 0,
                start=max(position, 0.0),
            )
        except pygame.error as exc:
            raise ValueError(f"Không thể phát nhạc nền: {exc}") from exc
        self._start_offset = position
        self._paused = False
        self._stopped = False

    def build_controls(
        self,
        page: ft.Page,
        on_choose_track: Callable[[ft.ControlEvent], None],
    ) -> ft.Column:
        track_label = ft.Text(
            self.file_path.name if self.file_path else "Chưa chọn tệp nhạc",
            color="#6B7280",
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        playback_button = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            tooltip="Phát / Tạm dừng",
        )
        stop_button = ft.IconButton(
            icon=ft.Icons.STOP,
            tooltip="Dừng",
        )
        previous_button = ft.IconButton(
            icon=ft.Icons.SKIP_PREVIOUS,
            tooltip="Bài trước / tua về đầu",
        )
        next_button = ft.IconButton(
            icon=ft.Icons.SKIP_NEXT,
            tooltip="Bài tiếp theo",
        )
        progress_label = ft.Text("00:00 / 00:00", size=12, color="#6B7280")
        progress_slider = ft.Slider(
            min=0,
            max=max(self.duration, 1),
            value=0,
            disabled=not self._loaded,
            divisions=None,
            on_change=lambda event: show_seek_position(event),
            on_change_end=lambda event: seek_track(event),
            expand=True,
        )
        volume_feedback = ft.Text("", size=12, color="#DC2626")
        volume_slider = ft.Slider(
            min=0,
            max=1,
            value=self.volume,
            divisions=20,
            label="{value}",
            on_change=lambda event: change_volume(event),
            on_change_end=lambda _: save_volume(),
            expand=True,
        )
        repeat_switch = ft.Switch(
            label="Lặp lại",
            value=self.repeat,
            on_change=lambda event: change_repeat(event),
        )
        feedback = ft.Text("", size=12, color="#DC2626")
        self._track_label = track_label
        self._progress_slider = progress_slider
        self._progress_label = progress_label
        self._playback_button = playback_button

        def format_time(seconds: float) -> str:
            total_seconds = max(int(seconds), 0)
            minutes, seconds_part = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"
            return f"{minutes:02d}:{seconds_part:02d}"

        def update_progress() -> None:
            if not self._loaded:
                return
            track_label.value = (
                self.file_path.name if self.file_path else "Chưa chọn tệp nhạc"
            )
            progress_slider.max = max(self.duration, 1)
            progress_slider.value = min(self.position(), self.duration)
            progress_slider.disabled = False
            progress_label.value = (
                f"{format_time(progress_slider.value)} / {format_time(self.duration)}"
            )
            page.update()

        def seek_track(event: ft.ControlEvent) -> None:
            try:
                self.seek(float(event.control.value))
                feedback.value = ""
            except (OSError, ValueError, pygame.error) as exc:
                feedback.value = f"Không thể tua nhạc: {exc}"
            update_progress()

        def show_seek_position(event: ft.ControlEvent) -> None:
            progress_label.value = (
                f"{format_time(float(event.control.value))} / "
                f"{format_time(self.duration)}"
            )
            page.update()

        def change_volume(event: ft.ControlEvent) -> None:
            try:
                self.set_volume(float(event.control.value))
                volume_feedback.value = ""
            except (OSError, ValueError, pygame.error) as exc:
                volume_feedback.value = f"Không thể đổi âm lượng: {exc}"

        def save_volume() -> None:
            try:
                save_preferences(music_volume=self.volume)
                volume_feedback.value = ""
            except OSError as exc:
                volume_feedback.value = f"Không thể lưu âm lượng: {exc}"
            page.update()

        def change_repeat(event: ft.ControlEvent) -> None:
            try:
                self.set_repeat(bool(event.control.value))
                feedback.value = ""
            except (OSError, ValueError, pygame.error) as exc:
                feedback.value = f"Không thể đổi chế độ lặp: {exc}"

        def toggle_playback(_: ft.ControlEvent) -> None:
            try:
                if self._paused or self._stopped:
                    self.play()
                    playback_button.icon = ft.Icons.PAUSE
                else:
                    self.pause()
                    playback_button.icon = ft.Icons.PLAY_ARROW
                feedback.value = ""
            except (OSError, ValueError, pygame.error) as exc:
                feedback.value = f"Không thể phát nhạc: {exc}"
            update_progress()

        def stop_playback(_: ft.ControlEvent) -> None:
            try:
                self.stop()
                playback_button.icon = ft.Icons.PLAY_ARROW
                feedback.value = ""
            except (OSError, pygame.error) as exc:
                feedback.value = f"Không thể dừng nhạc: {exc}"
            update_progress()

        def skip_previous(_: ft.ControlEvent) -> None:
            try:
                self.previous_track()
                playback_button.icon = ft.Icons.PAUSE
                feedback.value = ""
            except (OSError, ValueError) as exc:
                feedback.value = f"Không thể phát bài trước: {exc}"
            update_progress()

        def skip_next(_: ft.ControlEvent) -> None:
            try:
                self.next_track()
                playback_button.icon = ft.Icons.PAUSE
                feedback.value = ""
            except (OSError, ValueError) as exc:
                feedback.value = f"Không thể phát bài tiếp theo: {exc}"
            update_progress()

        playback_button.on_click = toggle_playback
        stop_button.on_click = stop_playback
        previous_button.on_click = skip_previous
        next_button.on_click = skip_next

        async def refresh_progress() -> None:
            while True:
                await asyncio.sleep(0.4)
                if self._loaded and not self._paused and not self._stopped:
                    if not pygame.mixer.music.get_busy() and not self.repeat:
                        try:
                            if not self.next_track(automatic=True):
                                playback_button.icon = ft.Icons.PLAY_ARROW
                            else:
                                playback_button.icon = ft.Icons.PAUSE
                                track_label.value = (
                                    self.file_path.name if self.file_path else ""
                                )
                        except (OSError, ValueError) as exc:
                            feedback.value = f"Không thể phát bài tiếp theo: {exc}"
                            self.stop()
                            playback_button.icon = ft.Icons.PLAY_ARROW
                    update_progress()

        page.run_task(refresh_progress)
        return ft.Column(
            [
                ft.Row(
                    [
                        track_label,
                        ft.OutlinedButton(
                            "Chọn nhạc",
                            icon=ft.Icons.MUSIC_NOTE,
                            on_click=on_choose_track,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        previous_button,
                        playback_button,
                        stop_button,
                        next_button,
                        progress_slider,
                        progress_label,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.VOLUME_DOWN, size=18),
                        volume_slider,
                        repeat_switch,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                feedback,
                volume_feedback,
            ],
            spacing=10,
        )

    def update_track_controls(self, file_path: str | Path) -> None:
        if (
            self._track_label is None
            or self._progress_slider is None
            or self._progress_label is None
        ):
            raise RuntimeError("Bảng điều khiển nhạc chưa được khởi tạo.")
        self._track_label.value = Path(file_path).name
        self._progress_slider.max = max(self.duration, 1)
        self._progress_slider.disabled = False
        self._progress_slider.value = 0
        self._progress_label.value = f"00:00 / {self._format_duration(self.duration)}"
        if self._playback_button is not None:
            self._playback_button.icon = ft.Icons.PLAY_ARROW

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(int(seconds), 0)
        minutes, seconds_part = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"
        return f"{minutes:02d}:{seconds_part:02d}"
