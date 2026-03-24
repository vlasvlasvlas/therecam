import threading
from typing import Optional

import cv2
import numpy as np


SAMPLE_RATE = 48000
BLOCK_SIZE = 256
MAX_HANDS = 2

BASE_FREQ = 220.0
PITCH_RANGE_SEMITONES = 36.0
ANTENNA_PITCH_X = 0.28
ANTENNA_VOLUME_Y = 0.88
ANTENNA_VOLUME_X_END = ANTENNA_PITCH_X
PITCH_DEADZONE = 0.02

MAX_AMP = 0.22
CTRL_SMOOTHING = 0.18
DELAY_SECONDS = 0.25
DELAY_FEEDBACK = 0.28
DELAY_MIX = 0.18

VIBRATO_DEPTH_DEFAULT = 0.20
VIBRATO_DEPTH_MIN = 0.0
VIBRATO_DEPTH_MAX = 2.5
VIBRATO_DEPTH_STEP = 0.08

VIBRATO_RATE_DEFAULT = 5.0
VIBRATO_RATE_MIN = 0.2
VIBRATO_RATE_MAX = 12.0
VIBRATO_RATE_STEP = 0.4

DELAY_MIX_MIN = 0.0
DELAY_MIX_MAX = 0.65
DELAY_MIX_STEP = 0.03

SNAP_BUFFER_SEMITONES_DEFAULT = 0.35
SNAP_BUFFER_SEMITONES_MIN = 0.05
SNAP_BUFFER_SEMITONES_MAX = 1.20
SNAP_BUFFER_SEMITONES_STEP = 0.05
SNAP_STRENGTH = 0.95

WAVEFORMS = ("sine", "triangle", "square", "saw")
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
BASE_FREQ_MIDI = 57  # A3 = 220 Hz
DIATONIC_STEPS = {0, 2, 4, 5, 7, 9, 11}
WINDOW_NAME = "Webcam Theremin (Python-only)"
HUD_MARGIN = 12
CONTROL_PANEL_WIDTH = 620
CONTROL_PANEL_LINE_HEIGHT = 24
ZONE_ALPHA = 0.10
HAND_BBOX_PAD = 18
GRID_NOTE_SCALE = 0.52
GRID_NOTE_THICKNESS = 2
PITCH_METRIC_COLOR = (255, 110, 255)
VOLUME_METRIC_COLOR = (255, 255, 0)


class SynthState:
    def __init__(self):
        self.lock = threading.Lock()
        self.freq = BASE_FREQ
        self.amp = 0.0
        self.target_freq = BASE_FREQ
        self.target_amp = 0.0
        self.phases = np.zeros(4, dtype=np.float64)
        self.delay_buffer = np.zeros(int(SAMPLE_RATE * DELAY_SECONDS), dtype=np.float32)
        self.delay_index = 0
        self.vibrato_phase = 0.0
        self.vibrato_depth = VIBRATO_DEPTH_DEFAULT
        self.vibrato_rate = VIBRATO_RATE_DEFAULT
        self.delay_mix = DELAY_MIX
        self.waveform = WAVEFORMS[0]


def distance_to_frequency(distance_norm: float) -> float:
    # Closer to pitch antenna means higher pitch (theremin behavior).
    d = float(np.clip(distance_norm, 0.0, 1.0))
    closeness = 1.0 - d
    semitone_offset = closeness * PITCH_RANGE_SEMITONES
    return BASE_FREQ * (2.0 ** (semitone_offset / 12.0))


def frequency_to_midi(freq: float) -> float:
    f = max(1e-6, float(freq))
    return 69.0 + (12.0 * np.log2(f / 440.0))


def midi_to_note_name(midi_value: int) -> str:
    octave = (midi_value // 12) - 1
    return f"{NOTE_NAMES[midi_value % 12]}{octave}"


def y_to_amplitude(y_value: float) -> float:
    y = float(np.clip(y_value, 0.0, 1.0))
    return (y**2) * MAX_AMP


def text_size(text: str, scale: float = 0.58, thickness: int = 2) -> tuple[int, int]:
    (width, height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    return width, height


def draw_outlined_text(
    image,
    text: str,
    origin: tuple[int, int],
    scale: float = 0.58,
    color=(225, 245, 255),
    thickness: int = 2,
    outline_color=(0, 0, 0),
    outline_thickness: Optional[int] = None,
):
    x, y = int(origin[0]), int(origin[1])
    if outline_thickness is None:
        outline_thickness = thickness + 2
    cv2.putText(
        image,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        outline_color,
        outline_thickness,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def fit_panel_rect(
    x: int,
    y: int,
    width: int,
    height: int,
    frame_width: int,
    frame_height: int,
    margin: int = HUD_MARGIN,
) -> tuple[int, int, int, int]:
    max_width = max(80, frame_width - (margin * 2))
    max_height = max(36, frame_height - (margin * 2))
    width = int(np.clip(width, 80, max_width))
    height = int(np.clip(height, 36, max_height))

    max_x = max(margin, frame_width - width - margin)
    max_y = max(margin, frame_height - height - margin)
    x = int(np.clip(x, margin, max_x))
    y = int(np.clip(y, margin, max_y))
    return x, y, width, height


def draw_level_bar(image, x, y, width, height, value, label):
    v = float(np.clip(value, 0.0, 1.0))
    cv2.rectangle(image, (x, y), (x + width, y + height), (80, 80, 80), 1)
    fill_h = int(height * v)
    if fill_h > 0:
        cv2.rectangle(
            image,
            (x + 2, y + height - fill_h + 2),
            (x + width - 2, y + height - 2),
            (0, 220, 120),
            -1,
        )
    draw_outlined_text(image, label, (x, y - 8), scale=0.55, color=(255, 255, 255), thickness=2)


def draw_pitch_line(image, width, height, pitch_x):
    x = int(np.clip(pitch_x, 0.0, 1.0) * width)
    cv2.line(image, (x, 0), (x, height), (255, 180, 0), 2)
    label = "PITCH X"
    label_w, _ = text_size(label, scale=0.5, thickness=2)
    label_x = int(np.clip(x + 8, 8, max(8, width - label_w - 8)))
    draw_outlined_text(image, label, (label_x, min(height - 10, 28)), scale=0.5, color=(255, 180, 0), thickness=2)


def draw_pitch_antenna(image, width, height):
    x = int(ANTENNA_PITCH_X * width)
    cv2.line(image, (x, 0), (x, height), (60, 220, 255), 3)
    label_y = max(60, min(height - 18, max(150, height // 4)))
    label_w, _ = text_size("PITCH ANT", scale=0.55, thickness=2)
    label_x = int(np.clip(x + 10, 10, max(10, width - label_w - 10)))
    draw_outlined_text(
        image,
        "PITCH ANT",
        (label_x, label_y),
        scale=0.55,
        color=(60, 220, 255),
        thickness=2,
    )


def draw_volume_antenna(image, width, height):
    y = int(ANTENNA_VOLUME_Y * height)
    x2 = int(ANTENNA_VOLUME_X_END * width)
    cv2.line(image, (0, y), (x2, y), (130, 200, 255), 3)
    label_y = max(60, min(height - 18, y - 110))
    draw_outlined_text(image, "VOL ANT", (10, label_y), scale=0.55, color=(60, 220, 255), thickness=2)


def distance_from_pitch_antenna(x_norm: float) -> float:
    raw = abs(float(np.clip(x_norm, 0.0, 1.0)) - ANTENNA_PITCH_X)
    max_dist = max(ANTENNA_PITCH_X, 1.0 - ANTENNA_PITCH_X)
    usable = max(0.0, raw - PITCH_DEADZONE)
    return float(np.clip(usable / max(1e-6, (max_dist - PITCH_DEADZONE)), 0.0, 1.0))


def volume_from_left_hand_y(y_norm: float) -> float:
    # Near horizontal antenna (bottom-left) = silence, top = full volume.
    y = float(np.clip(y_norm, 0.0, 1.0))
    usable = ANTENNA_VOLUME_Y
    v = (usable - y) / max(1e-6, usable)
    return float(np.clip(v, 0.0, 1.0))


def distance_norm_to_x_offset(distance_norm: float) -> float:
    d = float(np.clip(distance_norm, 0.0, 1.0))
    max_dist = max(ANTENNA_PITCH_X, 1.0 - ANTENNA_PITCH_X)
    return PITCH_DEADZONE + (d * (max_dist - PITCH_DEADZONE))


def apply_snap_to_grid(distance_norm: float, enabled: bool) -> tuple[float, float, bool]:
    semitone_offset = float(np.clip(distance_norm, 0.0, 1.0) * PITCH_RANGE_SEMITONES)
    nearest = round(semitone_offset)
    delta = nearest - semitone_offset
    snapped = False

    if enabled and abs(delta) <= SNAP_BUFFER_SEMITONES_DEFAULT:
        closeness = 1.0 - (abs(delta) / SNAP_BUFFER_SEMITONES_DEFAULT)
        semitone_offset += delta * (closeness * SNAP_STRENGTH)
        snapped = True

    distance_out = float(np.clip(semitone_offset / PITCH_RANGE_SEMITONES, 0.0, 1.0))
    return distance_out, semitone_offset, snapped


def nearest_snap_step(semitone_offset: float, mode: str) -> int:
    if mode == "diatonic":
        max_step = int(PITCH_RANGE_SEMITONES)
        candidates = [i for i in range(0, max_step + 1) if (i % 12) in DIATONIC_STEPS]
        return min(candidates, key=lambda x: abs(x - semitone_offset))
    return int(round(semitone_offset))


def apply_snap_to_grid_advanced(distance_norm: float, enabled: bool, snap_buffer: float, snap_mode: str) -> tuple[float, float, bool]:
    semitone_offset = float(np.clip(distance_norm, 0.0, 1.0) * PITCH_RANGE_SEMITONES)
    target = nearest_snap_step(semitone_offset, snap_mode)
    delta = float(target - semitone_offset)
    snapped = False

    if enabled and abs(delta) <= snap_buffer:
        closeness = 1.0 - (abs(delta) / snap_buffer)
        semitone_offset += delta * (closeness * SNAP_STRENGTH)
        snapped = True

    distance_out = float(np.clip(semitone_offset / PITCH_RANGE_SEMITONES, 0.0, 1.0))
    return distance_out, semitone_offset, snapped


def draw_note_grid(image, width: int, height: int):
    antenna_x = int(ANTENNA_PITCH_X * width)
    max_step = int(PITCH_RANGE_SEMITONES)

    for step in range(0, max_step + 1):
        # Higher semitone -> closer to antenna.
        d = 1.0 - (step / PITCH_RANGE_SEMITONES)
        x_off_norm = distance_norm_to_x_offset(d)
        x = int(antenna_x + (x_off_norm * width))

        midi_note = BASE_FREQ_MIDI + step
        is_octave_anchor = ((midi_note % 12) == 0)
        color = (255, 255, 255) if is_octave_anchor else (110, 110, 110)
        thickness = 2 if is_octave_anchor else 1

        if x < 0 or x > width:
            continue

        cv2.line(image, (x, 0), (x, height), color, thickness)

        if is_octave_anchor or (step % 2 == 0):
            note_name = midi_to_note_name(midi_note)
            draw_outlined_text(
                image,
                note_name,
                (x + 4, min(height - 10, 24 + (step % 3) * 18)),
                scale=GRID_NOTE_SCALE,
                color=(235, 235, 235),
                thickness=GRID_NOTE_THICKNESS,
                outline_thickness=GRID_NOTE_THICKNESS + 2,
            )


def draw_hud_panel(image, x: int, y: int, w: int, h: int, alpha: float = 0.72):
    frame_height, frame_width = image.shape[:2]
    x, y, w, h = fit_panel_rect(x, y, w, h, frame_width, frame_height)
    overlay = image.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0, image)
    return x, y, w, h


def clamp(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


def osc_from_phase(phase: np.ndarray, waveform: str) -> np.ndarray:
    if waveform == "triangle":
        return (2.0 / np.pi) * np.arcsin(np.sin(phase))
    if waveform == "square":
        return np.where(np.sin(phase) >= 0.0, 1.0, -1.0)
    if waveform == "saw":
        return 2.0 * ((phase / (2.0 * np.pi)) - np.floor((phase / (2.0 * np.pi)) + 0.5))
    return np.sin(phase)


def synth_voice(phase0: float, freq_array: np.ndarray, dt: float, waveform: str):
    increments = 2.0 * np.pi * freq_array * dt
    phase = phase0 + np.cumsum(increments)
    signal = osc_from_phase(phase, waveform)
    return signal, float(phase[-1] % (2.0 * np.pi))


def vibrato_multiplier(
    frames: int,
    dt: float,
    vibrato_phase: float,
    vibrato_rate: float,
    vibrato_depth: float,
) -> np.ndarray:
    if vibrato_depth <= 0.0:
        return np.ones(frames, dtype=np.float64)

    t = np.arange(frames, dtype=np.float64)
    vibrato_lfo = np.sin(vibrato_phase + (2.0 * np.pi * vibrato_rate * dt * t))
    return 2.0 ** ((vibrato_depth * vibrato_lfo) / 12.0)


def hud_line(image, text: str, y: int, color=(225, 245, 255), x: int = 20):
    draw_outlined_text(image, text, (x, y), scale=0.58, color=color, thickness=2)


def draw_control_zones(image, width: int, height: int):
    antenna_x = int(ANTENNA_PITCH_X * width)
    volume_y = int(ANTENNA_VOLUME_Y * height)
    overlay = image.copy()
    cv2.rectangle(overlay, (antenna_x, 0), (width - 1, height - 1), (20, 60, 120), -1)
    cv2.rectangle(overlay, (0, 0), (antenna_x, volume_y), (20, 95, 45), -1)
    cv2.addWeighted(overlay, ZONE_ALPHA, image, 1.0 - ZONE_ALPHA, 0, image)

    cv2.rectangle(image, (antenna_x, 0), (width - 1, height - 1), (255, 180, 0), 1)
    cv2.rectangle(image, (0, 0), (antenna_x, volume_y), (0, 220, 120), 1)

    pitch_label = "PITCH ZONE"
    pitch_label_w, _ = text_size(pitch_label, scale=0.55, thickness=2)
    pitch_label_x = int(np.clip(antenna_x + 10, 10, max(10, width - pitch_label_w - 10)))
    pitch_label_y = max(60, min(height - 24, height // 4))
    volume_label_y = max(60, min(height - 24, volume_y // 2))
    draw_outlined_text(image, pitch_label, (pitch_label_x, pitch_label_y), scale=0.55, color=(255, 180, 0), thickness=2)
    draw_outlined_text(image, "VOLUME ZONE", (10, volume_label_y), scale=0.55, color=(0, 220, 120), thickness=2)


def hand_bbox_from_landmarks(detected_hand, width: int, height: int, pad: int = HAND_BBOX_PAD) -> tuple[int, int, int, int]:
    xs = [landmark.x for landmark in detected_hand.landmark]
    ys = [landmark.y for landmark in detected_hand.landmark]
    x1 = max(0, int(min(xs) * width) - pad)
    y1 = max(0, int(min(ys) * height) - pad)
    x2 = min(width - 1, int(max(xs) * width) + pad)
    y2 = min(height - 1, int(max(ys) * height) + pad)
    return x1, y1, x2, y2


def draw_hand_bbox(image, bbox: tuple[int, int, int, int], label: str, color):
    x1, y1, x2, y2 = bbox
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

    label_w, _ = text_size(label, scale=0.52, thickness=2)
    tag_y = max(4, y1 - 28)
    tag_x2 = min(image.shape[1] - 4, x1 + label_w + 12)
    cv2.rectangle(image, (x1, tag_y), (tag_x2, tag_y + 24), (0, 0, 0), -1)
    cv2.rectangle(image, (x1, tag_y), (tag_x2, tag_y + 24), color, 1)
    draw_outlined_text(image, label, (x1 + 6, tag_y + 17), scale=0.52, color=color, thickness=2)


def fit_metric_scale(lines: list[str], box_width: int, box_height: int) -> float:
    if not lines:
        return 0.8

    candidate_scales = [1.6, 1.45, 1.3, 1.15, 1.0, 0.9, 0.8, 0.72]
    usable_width = max(48, box_width - 20)
    usable_height = max(48, box_height - 20)
    line_gap = 8

    for scale in candidate_scales:
        widths = [text_size(line, scale=scale, thickness=3)[0] for line in lines]
        heights = [text_size(line, scale=scale, thickness=3)[1] for line in lines]
        total_height = sum(heights) + (line_gap * (len(lines) - 1))
        if max(widths) <= usable_width and total_height <= usable_height:
            return scale

    return candidate_scales[-1]


def draw_hand_metric(image, bbox: tuple[int, int, int, int], lines: list[str], color):
    if not lines:
        return

    x1, y1, x2, y2 = bbox
    box_width = x2 - x1
    box_height = y2 - y1
    scale = fit_metric_scale(lines, box_width, box_height)
    thickness = 3
    line_gap = 8

    sizes = [text_size(line, scale=scale, thickness=thickness) for line in lines]
    line_widths = [size[0] for size in sizes]
    line_heights = [size[1] for size in sizes]
    total_height = sum(line_heights) + (line_gap * (len(lines) - 1))
    max_width = max(line_widths)

    panel_pad_x = 10
    panel_pad_y = 8
    panel_x1 = max(x1 + 4, x2 - max_width - (panel_pad_x * 2) - 4)
    panel_y1 = max(y1 + 4, y2 - total_height - (panel_pad_y * 2) - 4)
    panel_x2 = min(x2 - 4, x2 - 4)
    panel_y2 = min(y2 - 4, panel_y1 + total_height + (panel_pad_y * 2))

    overlay = image.copy()
    cv2.rectangle(overlay, (panel_x1, panel_y1), (panel_x2, panel_y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.74, image, 0.26, 0, image)
    cv2.rectangle(image, (panel_x1, panel_y1), (panel_x2, panel_y2), color, 1)

    current_y = panel_y2 - panel_pad_y - total_height + line_heights[0]
    for idx, line in enumerate(lines):
        line_width = line_widths[idx]
        line_height = line_heights[idx]
        line_x = panel_x2 - panel_pad_x - line_width
        draw_outlined_text(
            image,
            line,
            (line_x, current_y),
            scale=scale,
            color=color,
            thickness=thickness,
            outline_thickness=thickness + 3,
        )
        current_y += line_height + line_gap


def pitch_metric_lines(freq: float) -> list[str]:
    note_name = midi_to_note_name(int(round(frequency_to_midi(freq))))
    return [note_name, f"{freq:.1f} Hz"]


def volume_metric_text(volume_norm: float) -> str:
    return f"{int(round(np.clip(volume_norm, 0.0, 1.0) * 100.0))}%"


def resolve_hand_roles(hand_infos: list[dict]) -> tuple[int, int]:
    if not hand_infos:
        raise ValueError("hand_infos no puede estar vacio")
    if len(hand_infos) == 1:
        return 0, 0

    left_idx = next((i for i, hand in enumerate(hand_infos) if hand["handedness"] == "Left"), None)
    right_idx = next((i for i, hand in enumerate(hand_infos) if hand["handedness"] == "Right"), None)
    by_x = sorted(range(len(hand_infos)), key=lambda i: hand_infos[i]["x"])

    volume_idx = left_idx if left_idx is not None else by_x[0]
    pitch_idx = right_idx if right_idx is not None else by_x[-1]

    if volume_idx == pitch_idx:
        volume_idx = by_x[0]
        pitch_idx = by_x[-1]
    return volume_idx, pitch_idx


def waveform_from_key(key: int, current_waveform: str) -> Optional[str]:
    direct_waveforms = {
        ord("u"): "sine",
        ord("U"): "sine",
        ord("i"): "triangle",
        ord("I"): "triangle",
        ord("o"): "square",
        ord("O"): "square",
        ord("p"): "saw",
        ord("P"): "saw",
    }
    if key in direct_waveforms:
        return direct_waveforms[key]
    if key in (ord("z"), ord("Z")):
        idx = (WAVEFORMS.index(current_waveform) + 1) % len(WAVEFORMS)
        return WAVEFORMS[idx]
    return None


def main() -> None:
    import mediapipe as mp
    import sounddevice as sd

    state = SynthState()
    show_note_grid = True
    snap_to_grid = False
    fullscreen = False
    snap_buffer = SNAP_BUFFER_SEMITONES_DEFAULT
    snap_mode = "chromatic"

    def audio_callback(outdata, frames, _time, status):
        if status:
            print(f"Audio status: {status}")

        with state.lock:
            current_freq = state.freq
            current_amp = state.amp
            target_freq = state.target_freq
            target_amp = state.target_amp
            phases = state.phases.copy()
            delay_buffer = state.delay_buffer
            delay_index = state.delay_index
            vibrato_phase = state.vibrato_phase
            vibrato_depth = state.vibrato_depth
            vibrato_rate = state.vibrato_rate
            delay_mix = state.delay_mix
            waveform = state.waveform

        # Smooth control changes so the instrument feels stable.
        current_freq += (target_freq - current_freq) * CTRL_SMOOTHING
        current_amp += (target_amp - current_amp) * CTRL_SMOOTHING

        dt = 1.0 / SAMPLE_RATE

        vibrato_factor = vibrato_multiplier(frames, dt, vibrato_phase, vibrato_rate, vibrato_depth)

        # Rich but lightweight voice: fundamental + detuned pair + sub osc.
        f1 = current_freq * vibrato_factor
        f2 = (current_freq * 0.997) * vibrato_factor
        f3 = (current_freq * 1.003) * vibrato_factor
        f4 = np.maximum(30.0, (current_freq * 0.5) * vibrato_factor)

        s1, p1 = synth_voice(phases[0], f1, dt, waveform)
        s2, p2 = synth_voice(phases[1], f2, dt, waveform)
        s3, p3 = synth_voice(phases[2], f3, dt, waveform)
        sub, p4 = synth_voice(phases[3], f4, dt, waveform)

        dry = 0.52 * s1 + 0.22 * s2 + 0.22 * s3 + 0.18 * sub

        # Soft saturation to keep levels musical and avoid harsh clipping.
        dry = np.tanh(dry * 1.35)
        dry = dry * current_amp

        # Small delay for width without high CPU cost.
        wet = np.empty(frames, dtype=np.float32)
        for i in range(frames):
            delayed = delay_buffer[delay_index]
            y = dry[i] + (delayed * delay_mix)
            wet[i] = y
            delay_buffer[delay_index] = np.float32(dry[i] + delayed * DELAY_FEEDBACK)
            delay_index += 1
            if delay_index >= delay_buffer.size:
                delay_index = 0

        # Final safety limiter.
        out = np.tanh(wet * 1.1).astype(np.float32)

        outdata[:, 0] = out

        final_phases = np.array([p1, p2, p3, p4], dtype=np.float64)
        final_vibrato_phase = float((vibrato_phase + (2.0 * np.pi * vibrato_rate * dt * frames)) % (2.0 * np.pi))

        with state.lock:
            state.freq = current_freq
            state.amp = current_amp
            state.phases = final_phases
            state.delay_index = delay_index
            state.vibrato_phase = final_vibrato_phase

    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        raise RuntimeError("No se pudo abrir la camara.")

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=MAX_HANDS,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    mp_draw = mp.solutions.drawing_utils

    print("Modo Python-only iniciado.")
    print("2 manos: derecha=tono (cerca de antena vertical = mas agudo), izquierda=volumen.")
    print("1 mano: controla tono+volumen.")
    print("Teclas (solo letras): R/F vibrato depth, T/G vibrato rate, Y/H delay mix.")
    print("Sonido: Z ciclo waveform, U sine, I triangle, O square, P saw. Grid: M toggle, snap N toggle, B/V snap buffer.")
    print("Modo snap: K chromatic/diatonic. Pantalla: L fullscreen. Salir: Q.")
    print("Salir: presiona q en la ventana de webcam.")
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=BLOCK_SIZE,
            dtype="float32",
            callback=audio_callback,
            latency="low",
        ):
            while True:
                ok, image = capture.read()
                if not ok:
                    continue

                image = cv2.flip(image, 1)
                height, width = image.shape[:2]

                if show_note_grid:
                    draw_note_grid(image, width, height)
                draw_control_zones(image, width, height)
                draw_pitch_antenna(image, width, height)
                draw_volume_antenna(image, width, height)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                image_rgb.flags.writeable = False
                results = hands.process(image_rgb)

                if results.multi_hand_landmarks:
                    hand_infos = []
                    handedness_list = results.multi_handedness or []
                    for idx, detected_hand in enumerate(results.multi_hand_landmarks):
                        handedness = "Unknown"
                        if idx < len(handedness_list) and handedness_list[idx].classification:
                            handedness = handedness_list[idx].classification[0].label

                        index_tip = detected_hand.landmark[8]
                        hand_infos.append(
                            {
                                "x": float(index_tip.x),
                                "y": float(index_tip.y),
                                "landmarks": detected_hand,
                                "handedness": handedness,
                                "bbox": hand_bbox_from_landmarks(detected_hand, width, height),
                            }
                        )

                    volume_idx, pitch_idx = resolve_hand_roles(hand_infos)
                    volume_hand = hand_infos[volume_idx]
                    pitch_hand = hand_infos[pitch_idx]

                    pitch_x = pitch_hand["x"]
                    volume_y = volume_from_left_hand_y(volume_hand["y"])
                    pitch_distance = distance_from_pitch_antenna(pitch_x)
                    pitch_distance_proc, semitone_offset_proc, snapped_now = apply_snap_to_grid_advanced(
                        pitch_distance,
                        snap_to_grid,
                        snap_buffer,
                        snap_mode,
                    )

                    target_freq = distance_to_frequency(pitch_distance_proc)
                    target_amp = y_to_amplitude(volume_y)

                    with state.lock:
                        state.target_freq = target_freq
                        state.target_amp = target_amp

                    for idx, hand_info in enumerate(hand_infos):
                        detected_hand = hand_info["landmarks"]
                        mp_draw.draw_landmarks(image, detected_hand, mp_hands.HAND_CONNECTIONS)

                        roles = []
                        if idx == pitch_idx:
                            roles.append("PITCH")
                        if idx == volume_idx:
                            roles.append("VOL")
                        role_label = "+".join(roles) if roles else hand_info["handedness"].upper()
                        handedness_label = hand_info["handedness"].upper()
                        if handedness_label != "UNKNOWN":
                            role_label = f"{role_label} | {handedness_label}"

                        if idx == pitch_idx and idx == volume_idx:
                            box_color = (255, 255, 0)
                        elif idx == pitch_idx:
                            box_color = (0, 180, 255)
                        else:
                            box_color = (0, 220, 120)

                        draw_hand_bbox(image, hand_info["bbox"], role_label, box_color)

                        metric_lines = []
                        metric_color = PITCH_METRIC_COLOR if idx == pitch_idx else VOLUME_METRIC_COLOR
                        if idx == pitch_idx:
                            metric_lines.extend(pitch_metric_lines(target_freq))
                        if idx == volume_idx:
                            volume_text = volume_metric_text(volume_y)
                            if idx == pitch_idx:
                                metric_lines.append(f"VOL {volume_text}")
                            else:
                                metric_lines = [volume_text]
                                metric_color = VOLUME_METRIC_COLOR

                        draw_hand_metric(image, hand_info["bbox"], metric_lines, metric_color)

                        tip = detected_hand.landmark[8]
                        px = int(tip.x * width)
                        py = int(tip.y * height)
                        cv2.circle(image, (px, py), 8, box_color, 2)

                    snap_label = "SNAPPED" if snapped_now else "FREE"
                    if len(hand_infos) >= 2:
                        mode_text = "2-HAND: RIGHT hand = PITCH | LEFT hand = VOL"
                    else:
                        single_hand = hand_infos[0]["handedness"].upper()
                        mode_text = f"1-HAND: {single_hand} hand drives PITCH + VOL"

                    status_x, status_y, status_w, _ = draw_hud_panel(image, 12, 10, 720, 94, alpha=0.80)
                    draw_outlined_text(
                        image,
                        mode_text,
                        (status_x + 10, status_y + 24),
                        scale=0.58,
                        color=(255, 255, 255),
                        thickness=2,
                    )
                    draw_outlined_text(
                        image,
                        f"Amp: {target_amp:0.3f} | Dist: {pitch_distance_proc:0.2f} | Snap: {snap_label} | {snap_mode.upper()}",
                        (status_x + 10, status_y + 52),
                        scale=0.58,
                        color=(120, 255, 120) if snapped_now else (235, 235, 235),
                        thickness=2,
                    )

                    draw_pitch_line(image, width, height, pitch_x)
                    draw_level_bar(image, status_x + status_w - 42, status_y + 24, 26, 58, volume_y, "VOL")
                else:
                    with state.lock:
                        state.target_amp = 0.0

                    status_x, status_y, _, _ = draw_hud_panel(image, 12, 10, 360, 48, alpha=0.82)
                    draw_outlined_text(
                        image,
                        "No hands detected",
                        (status_x + 10, status_y + 30),
                        scale=0.7,
                        color=(80, 80, 255),
                        thickness=2,
                    )

                with state.lock:
                    vib_depth = state.vibrato_depth
                    vib_rate = state.vibrato_rate
                    delay_mix_ui = state.delay_mix
                    waveform_ui = state.waveform

                if not fullscreen:
                    control_lines = [
                        f"SONIDO: {waveform_ui.upper()} [Z ciclo | U/I/O/P directo]",
                        f"Vibrato Depth: {vib_depth:.2f} st [R/F]",
                        f"Vibrato Rate:  {vib_rate:.1f} Hz [T/G]",
                        f"Delay Mix:     {delay_mix_ui:.2f} [Y/H]",
                        f"Grid [M]: {'ON' if show_note_grid else 'OFF'} | Snap [N]: {'ON' if snap_to_grid else 'OFF'}",
                        f"Snap Buffer: {snap_buffer:.2f} st [B/V] | Mode [K]: {snap_mode.upper()}",
                        "Fullscreen [L] | Exit [Q]",
                    ]
                    control_h = 18 + (len(control_lines) * CONTROL_PANEL_LINE_HEIGHT)
                    control_x, control_y, _, _ = draw_hud_panel(
                        image,
                        width - CONTROL_PANEL_WIDTH - HUD_MARGIN,
                        height - control_h - HUD_MARGIN,
                        CONTROL_PANEL_WIDTH,
                        control_h,
                        alpha=0.58,
                    )
                    for line_idx, line in enumerate(control_lines):
                        line_color = (200, 200, 120) if line_idx == len(control_lines) - 1 else (225, 245, 255)
                        hud_line(image, line, control_y + 24 + (line_idx * CONTROL_PANEL_LINE_HEIGHT), color=line_color, x=control_x + 10)
                else:
                    exit_x, exit_y, _, _ = draw_hud_panel(image, 12, height - 52, 520, 36, alpha=0.86)
                    draw_outlined_text(
                        image,
                        "FULLSCREEN  |  L: exit fullscreen  |  Q: quit",
                        (exit_x + 8, exit_y + 24),
                        scale=0.58,
                        color=(240, 240, 240),
                        thickness=2,
                    )

                cv2.imshow(WINDOW_NAME, image)
                key = cv2.waitKeyEx(1)

                if key in (ord("q"), ord("Q")):
                    break

                with state.lock:
                    if key in (ord("r"), ord("R")):
                        state.vibrato_depth = clamp(state.vibrato_depth + VIBRATO_DEPTH_STEP, VIBRATO_DEPTH_MIN, VIBRATO_DEPTH_MAX)
                    elif key in (ord("f"), ord("F")):
                        state.vibrato_depth = clamp(state.vibrato_depth - VIBRATO_DEPTH_STEP, VIBRATO_DEPTH_MIN, VIBRATO_DEPTH_MAX)
                    elif key in (ord("h"), ord("H")):
                        state.delay_mix = clamp(state.delay_mix - DELAY_MIX_STEP, DELAY_MIX_MIN, DELAY_MIX_MAX)
                    elif key in (ord("y"), ord("Y")):
                        state.delay_mix = clamp(state.delay_mix + DELAY_MIX_STEP, DELAY_MIX_MIN, DELAY_MIX_MAX)
                    elif key in (ord("g"), ord("G")):
                        state.vibrato_rate = clamp(state.vibrato_rate - VIBRATO_RATE_STEP, VIBRATO_RATE_MIN, VIBRATO_RATE_MAX)
                    elif key in (ord("t"), ord("T")):
                        state.vibrato_rate = clamp(state.vibrato_rate + VIBRATO_RATE_STEP, VIBRATO_RATE_MIN, VIBRATO_RATE_MAX)

                    next_waveform = waveform_from_key(key, state.waveform)
                    if next_waveform is not None:
                        state.waveform = next_waveform

                if key in (ord("m"), ord("M")):
                    show_note_grid = not show_note_grid
                elif key in (ord("n"), ord("N")):
                    snap_to_grid = not snap_to_grid
                elif key in (ord("b"), ord("B")):
                    snap_buffer = clamp(snap_buffer - SNAP_BUFFER_SEMITONES_STEP, SNAP_BUFFER_SEMITONES_MIN, SNAP_BUFFER_SEMITONES_MAX)
                elif key in (ord("v"), ord("V")):
                    snap_buffer = clamp(snap_buffer + SNAP_BUFFER_SEMITONES_STEP, SNAP_BUFFER_SEMITONES_MIN, SNAP_BUFFER_SEMITONES_MAX)
                elif key in (ord("k"), ord("K")):
                    snap_mode = "diatonic" if snap_mode == "chromatic" else "chromatic"
                elif key in (ord("l"), ord("L")):
                    fullscreen = not fullscreen
                    cv2.setWindowProperty(
                        WINDOW_NAME,
                        cv2.WND_PROP_FULLSCREEN,
                        cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
                    )
    finally:
        hands.close()
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
