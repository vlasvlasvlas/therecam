import unittest

import numpy as np

import webcam_theremin_python as app


class HandRoleTests(unittest.TestCase):
    def test_resolve_hand_roles_prefers_handedness(self):
        hand_infos = [
            {"x": 0.82, "handedness": "Left"},
            {"x": 0.18, "handedness": "Right"},
        ]

        volume_idx, pitch_idx = app.resolve_hand_roles(hand_infos)

        self.assertEqual(volume_idx, 0)
        self.assertEqual(pitch_idx, 1)

    def test_resolve_hand_roles_falls_back_to_screen_position(self):
        hand_infos = [
            {"x": 0.74, "handedness": "Unknown"},
            {"x": 0.21, "handedness": "Unknown"},
        ]

        volume_idx, pitch_idx = app.resolve_hand_roles(hand_infos)

        self.assertEqual(volume_idx, 1)
        self.assertEqual(pitch_idx, 0)

    def test_resolve_hand_roles_single_hand_controls_both(self):
        volume_idx, pitch_idx = app.resolve_hand_roles([{"x": 0.50, "handedness": "Left"}])
        self.assertEqual((volume_idx, pitch_idx), (0, 0))


class WaveformKeyTests(unittest.TestCase):
    def test_waveform_shortcuts_match_hud(self):
        self.assertEqual(app.waveform_from_key(ord("z"), "saw"), "sine")
        self.assertEqual(app.waveform_from_key(ord("u"), "saw"), "sine")
        self.assertEqual(app.waveform_from_key(ord("i"), "sine"), "triangle")
        self.assertEqual(app.waveform_from_key(ord("o"), "sine"), "square")
        self.assertEqual(app.waveform_from_key(ord("p"), "sine"), "saw")
        self.assertIsNone(app.waveform_from_key(ord("x"), "sine"))


class SoundShortcutTests(unittest.TestCase):
    def test_synth_defaults_start_dry(self):
        state = app.SynthState()
        self.assertEqual(state.vibrato_depth, 0.0)
        self.assertEqual(state.delay_mix, 0.0)

    def test_direct_off_shortcuts_disable_vibrato_and_delay(self):
        state = app.SynthState()
        state.vibrato_depth = 0.64
        state.delay_mix = 0.31

        app.apply_sound_shortcut(state, ord("j"))
        app.apply_sound_shortcut(state, ord("d"))

        self.assertEqual(state.vibrato_depth, 0.0)
        self.assertEqual(state.delay_mix, 0.0)

    def test_increment_shortcuts_can_add_vibrato_and_delay_from_zero(self):
        state = app.SynthState()

        app.apply_sound_shortcut(state, ord("r"))
        app.apply_sound_shortcut(state, ord("y"))

        self.assertGreater(state.vibrato_depth, 0.0)
        self.assertGreater(state.delay_mix, 0.0)


class VibratoTests(unittest.TestCase):
    def test_zero_depth_vibrato_keeps_full_buffer_length(self):
        frames = 16
        factor = app.vibrato_multiplier(
            frames=frames,
            dt=1.0 / app.SAMPLE_RATE,
            vibrato_phase=0.0,
            vibrato_rate=app.VIBRATO_RATE_DEFAULT,
            vibrato_depth=0.0,
        )

        self.assertEqual(factor.shape, (frames,))
        self.assertTrue(np.allclose(factor, np.ones(frames)))

    def test_positive_depth_vibrato_keeps_full_buffer_length(self):
        frames = 16
        factor = app.vibrato_multiplier(
            frames=frames,
            dt=1.0 / app.SAMPLE_RATE,
            vibrato_phase=0.0,
            vibrato_rate=app.VIBRATO_RATE_DEFAULT,
            vibrato_depth=app.VIBRATO_DEPTH_DEFAULT,
        )

        self.assertEqual(factor.shape, (frames,))


class LayoutTests(unittest.TestCase):
    def test_fit_panel_rect_keeps_panel_inside_frame(self):
        x, y, width, height = app.fit_panel_rect(12, 400, 900, 220, 640, 480)

        self.assertGreaterEqual(x, app.HUD_MARGIN)
        self.assertGreaterEqual(y, app.HUD_MARGIN)
        self.assertLessEqual(x + width + app.HUD_MARGIN, 640)
        self.assertLessEqual(y + height + app.HUD_MARGIN, 480)

    def test_draw_control_zones_marks_both_interaction_areas(self):
        image = np.zeros((240, 320, 3), dtype=np.uint8)

        app.draw_control_zones(image, 320, 240)

        left_zone_sum = int(image[:180, :90].sum())
        right_zone_sum = int(image[:, 120:].sum())
        self.assertGreater(left_zone_sum, 0)
        self.assertGreater(right_zone_sum, 0)


if __name__ == "__main__":
    unittest.main()
