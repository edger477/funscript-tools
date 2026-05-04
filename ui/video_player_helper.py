"""
Shared video-playback behavior for Toplevel viewers.

Both ShaftViewer and TrochoidViewer had nearly identical implementations
of the open/clear/browse/drop/frame-update/sync-here handlers. This
mixin centralizes them.

Subclasses (inheriting from tk.Toplevel + VideoPlaybackMixin) must
initialize these attributes in __init__ before the first frame update:

    self._video_path:            Optional[str]
    self._video_cap:             Optional[cv2.VideoCapture]
    self._video_fps:             float
    self._video_duration:        float
    self._video_offset_var:      tk.DoubleVar
    self._video_last_frame_time: float
    self._video_widget:          tk.Label  (where frames get drawn)
    self._video_photo:           Optional[ImageTk.PhotoImage]
    self._video_path_lbl:        ttk.Label  (shows current file name)
    self._playhead_t:            float

Optional:
    self._show_video_var:        tk.BooleanVar — when False, skip decode
    _log_prefix (class attr):    prefix for console log messages

Grid re-layout for the Show-Video toggle is kept per-viewer because
each viewer manages its own grid differently; only the decode gate
lives in the shared `_update_video_frame`.
"""

import os
import tkinter as tk
from tkinter import filedialog

try:
    import cv2
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False

try:
    from PIL import Image, ImageTk
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False


class VideoPlaybackMixin:
    """Shared video handlers for viewers that display a single scrubbable
    video synced to a funscript playhead."""

    _log_prefix = '[video]'

    def _open_video(self, path):
        if not (_HAVE_CV2 and _HAVE_PIL):
            return
        # Close any previous capture.
        if self._video_cap is not None:
            try:
                self._video_cap.release()
            except Exception:
                pass
        self._video_cap = None
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                raise RuntimeError("cv2.VideoCapture failed to open")
            self._video_cap = cap
            self._video_path = path
            self._video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            self._video_duration = (frame_count / self._video_fps
                                     if self._video_fps > 0 else 0.0)
            self._video_path_lbl.config(
                text=os.path.basename(path), foreground='#222')
            self._video_last_frame_time = -1.0
            self._update_video_frame(force=True)
        except Exception as e:
            print(f"{self._log_prefix} video open failed: {e}")
            self._video_widget.config(
                text=f"(failed to open video: {e})", image='')

    def _clear_video(self):
        if self._video_cap is not None:
            try:
                self._video_cap.release()
            except Exception:
                pass
        self._video_cap = None
        self._video_path = None
        self._video_photo = None
        self._video_last_frame_time = -1.0
        self._video_path_lbl.config(text="(none)", foreground='#666')
        placeholder = ("Drop a video file here  (.mp4 / .mov / .mkv / ...)"
                       if _HAVE_CV2 and _HAVE_PIL
                       else "Video playback unavailable — install "
                            "opencv-python + Pillow")
        self._video_widget.config(image='', text=placeholder)

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Select video file",
            filetypes=[("Video files",
                        "*.mp4 *.mov *.mkv *.m4v *.avi *.webm"),
                       ("All files", "*.*")],
            parent=self)
        if path:
            self._open_video(path)

    def _on_video_drop(self, event):
        raw = (event.data or "").strip()
        if raw.startswith('{') and raw.endswith('}'):
            raw = raw[1:-1]
        if '} {' in raw:
            raw = raw.split('} {')[0]
        elif ' ' in raw and not os.path.exists(raw):
            raw = raw.split()[0]
        if os.path.isfile(raw):
            self._open_video(raw)

    def _update_video_frame(self, force=False):
        if self._video_cap is None or not (_HAVE_CV2 and _HAVE_PIL):
            return
        # Skip decode while the panel is hidden (Show-Video toggle off).
        if hasattr(self, '_show_video_var') and not bool(
                self._show_video_var.get()):
            return
        try:
            offset = float(self._video_offset_var.get())
        except (tk.TclError, ValueError):
            offset = 0.0
        t_signal = float(self._playhead_t)
        video_t = t_signal + offset
        if video_t < 0:
            video_t = 0.0
        if self._video_duration > 0:
            video_t = min(video_t, self._video_duration - 1e-3)
        # Throttle: only seek if the target time differs from the last
        # drawn frame by more than half a frame.
        if (not force and self._video_fps > 0
                and abs(video_t - self._video_last_frame_time)
                < (0.5 / self._video_fps)):
            return
        try:
            self._video_cap.set(cv2.CAP_PROP_POS_MSEC, video_t * 1000.0)
            ok, frame = self._video_cap.read()
            if not ok or frame is None:
                return
            # cv2 → RGB, fit to the label size while preserving aspect.
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]
            wid_w = max(1, self._video_widget.winfo_width())
            wid_h = max(1, self._video_widget.winfo_height())
            if wid_w > 20 and wid_h > 20:
                scale = min(wid_w / w, wid_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                img = Image.fromarray(frame).resize(
                    (new_w, new_h), Image.BILINEAR)
            else:
                img = Image.fromarray(frame)
            self._video_photo = ImageTk.PhotoImage(img)
            self._video_widget.config(image=self._video_photo, text='')
            self._video_last_frame_time = video_t
        except Exception as e:
            print(f"{self._log_prefix} video frame failed: {e}")

    def _sync_here(self):
        """Set video offset so the current video frame lines up with the
        current signal playhead time.

        Reads the actual video time from the capture (may be snapped to
        the nearest keyframe depending on codec), and computes
            offset = actual_video_time − signal_time
        so subsequent video_t = signal_time + offset reproduces it.
        """
        if self._video_cap is None or not _HAVE_CV2:
            return
        try:
            pos_ms = float(self._video_cap.get(cv2.CAP_PROP_POS_MSEC))
        except Exception:
            return
        actual_video_t = pos_ms / 1000.0
        signal_t = float(self._playhead_t)
        new_offset = actual_video_t - signal_t
        try:
            self._video_offset_var.set(round(new_offset, 3))
        except tk.TclError:
            pass
        self._update_video_frame(force=True)
