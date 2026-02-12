import unittest
from types import SimpleNamespace

import numpy as np

from capstone_proj.control import JointSpacePDController


def _model(limit: float = 5.0):
    ctrlrange = np.tile(np.array([[-limit, limit]], dtype=float), (14, 1))
    return SimpleNamespace(nu=14, nv=14, actuator_ctrlrange=ctrlrange)


def _data(qpos=None, qvel=None, qfrc_bias=None):
    if qpos is None:
        qpos = np.zeros(14, dtype=float)
    if qvel is None:
        qvel = np.zeros(14, dtype=float)
    if qfrc_bias is None:
        qfrc_bias = np.zeros(14, dtype=float)
    return SimpleNamespace(
        qpos=np.asarray(qpos, dtype=float),
        qvel=np.asarray(qvel, dtype=float),
        qfrc_bias=np.asarray(qfrc_bias, dtype=float),
    )


class JointSpacePDControllerTest(unittest.TestCase):
    def test_compute_returns_full_vector_with_clipping(self):
        controller = JointSpacePDController(_model(), left_kp=100.0, right_kp=100.0, left_kd=0.0, right_kd=0.0)
        data = _data()

        tau = controller.compute(data, np.ones(7), np.ones(7))

        self.assertEqual(tau.shape, (14,))
        self.assertTrue(np.allclose(tau, np.full(14, 5.0)))

    def test_right_sign_is_applied(self):
        controller = JointSpacePDController(
            _model(limit=20.0),
            left_kp=1.0,
            left_kd=0.0,
            right_kp=1.0,
            right_kd=0.0,
            right_sign=np.array([-1, 1, 1, 1, 1, 1, 1], dtype=float),
        )
        data = _data()

        tau = controller.compute(data, np.zeros(7), np.array([1, 2, 0, 0, 0, 0, 0], dtype=float))

        self.assertAlmostEqual(tau[7], -1.0)
        self.assertAlmostEqual(tau[8], 2.0)

    def test_bad_desired_vector_shape_raises(self):
        controller = JointSpacePDController(_model())
        data = _data()

        with self.assertRaises(ValueError):
            controller.compute(data, np.zeros(6), np.zeros(7))


if __name__ == "__main__":
    unittest.main()

