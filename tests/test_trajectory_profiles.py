import unittest

import numpy as np

from capstone_proj.simulation.run_pid import compute_desired_targets


class TrajectoryProfilesTest(unittest.TestCase):
    def setUp(self):
        self.base_left = np.zeros(7, dtype=float)
        self.base_right = np.zeros(7, dtype=float)

    def test_static_applies_joint_offset(self):
        q_left, q_right = compute_desired_targets(
            base_left=self.base_left,
            base_right=self.base_right,
            t_sec=0.0,
            trajectory="static",
            joint_offset=0.25,
            amp_a=0.3,
            amp_b=0.2,
            frequency_hz=0.2,
            joint_a=0,
            joint_b=1,
            right_mode="same",
            phase_offset_rad=0.0,
        )

        self.assertAlmostEqual(q_left[0], 0.25)
        self.assertAlmostEqual(q_right[0], 0.25)
        self.assertTrue(np.allclose(q_left[1:], 0.0))

    def test_circle_updates_joint_plane(self):
        q_left, q_right = compute_desired_targets(
            base_left=self.base_left,
            base_right=self.base_right,
            t_sec=0.0,
            trajectory="circle",
            joint_offset=0.0,
            amp_a=0.4,
            amp_b=0.2,
            frequency_hz=0.5,
            joint_a=2,
            joint_b=3,
            right_mode="same",
            phase_offset_rad=0.0,
        )

        # At t=0 for cosine/sine parameterization: x=amp, y=0
        self.assertAlmostEqual(q_left[2], 0.4)
        self.assertAlmostEqual(q_left[3], 0.0)
        self.assertAlmostEqual(q_right[2], 0.4)
        self.assertAlmostEqual(q_right[3], 0.0)

    def test_mirror_flips_right_x_component(self):
        q_left, q_right = compute_desired_targets(
            base_left=self.base_left,
            base_right=self.base_right,
            t_sec=0.0,
            trajectory="ellipse",
            joint_offset=0.0,
            amp_a=0.3,
            amp_b=0.1,
            frequency_hz=0.4,
            joint_a=0,
            joint_b=1,
            right_mode="mirror",
            phase_offset_rad=0.0,
        )

        self.assertAlmostEqual(q_left[0], 0.3)
        self.assertAlmostEqual(q_right[0], -0.3)
        self.assertAlmostEqual(q_left[1], q_right[1])

    def test_invalid_joint_index_raises(self):
        with self.assertRaises(ValueError):
            compute_desired_targets(
                base_left=self.base_left,
                base_right=self.base_right,
                t_sec=0.0,
                trajectory="circle",
                joint_offset=0.0,
                amp_a=0.3,
                amp_b=0.2,
                frequency_hz=0.2,
                joint_a=7,
                joint_b=1,
                right_mode="same",
                phase_offset_rad=0.0,
            )


if __name__ == "__main__":
    unittest.main()

