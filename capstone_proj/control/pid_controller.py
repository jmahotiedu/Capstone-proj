"""Joint-space PD controller for a 14-DoF bimanual setup."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


def _normalize_ids(ids: Iterable[int] | None, default: Sequence[int], name: str) -> np.ndarray:
    if ids is None:
        arr = np.asarray(default, dtype=int)
    else:
        arr = np.asarray(list(ids), dtype=int)
    if arr.shape != (7,):
        raise ValueError(f"{name} must have exactly 7 entries, got shape {arr.shape}")
    if np.any(arr < 0):
        raise ValueError(f"{name} cannot contain negative indices")
    return arr


def _as_7d_vector(values: Sequence[float], name: str) -> np.ndarray:
    vec = np.asarray(values, dtype=float)
    if vec.shape != (7,):
        raise ValueError(f"{name} must be shape (7,), got {vec.shape}")
    return vec


class JointSpacePDController:
    """Bimanual joint-space PD controller with bias-force compensation."""

    def __init__(
        self,
        model,
        left_joint_ids: Iterable[int] | None = None,
        right_joint_ids: Iterable[int] | None = None,
        left_actuator_ids: Iterable[int] | None = None,
        right_actuator_ids: Iterable[int] | None = None,
        left_kp: float = 20.0,
        left_kd: float = 10.0,
        right_kp: float = 20.0,
        right_kd: float = 10.0,
        right_sign: Sequence[float] | None = None,
    ) -> None:
        self.model = model

        self.left_joint_ids = _normalize_ids(left_joint_ids, range(0, 7), "left_joint_ids")
        self.right_joint_ids = _normalize_ids(right_joint_ids, range(7, 14), "right_joint_ids")
        self.left_actuator_ids = _normalize_ids(left_actuator_ids, range(0, 7), "left_actuator_ids")
        self.right_actuator_ids = _normalize_ids(right_actuator_ids, range(7, 14), "right_actuator_ids")

        joint_ids_all = np.concatenate((self.left_joint_ids, self.right_joint_ids))
        actuator_ids_all = np.concatenate((self.left_actuator_ids, self.right_actuator_ids))
        if len(np.unique(joint_ids_all)) != 14:
            raise ValueError("Joint ids must be unique across both arms.")
        if len(np.unique(actuator_ids_all)) != 14:
            raise ValueError("Actuator ids must be unique across both arms.")

        if int(np.max(joint_ids_all)) >= int(model.nv):
            raise ValueError("Joint ids exceed model.nv.")
        if int(np.max(actuator_ids_all)) >= int(model.nu):
            raise ValueError("Actuator ids exceed model.nu.")

        self.Kp_left = np.full(7, float(left_kp), dtype=float)
        self.Kd_left = np.full(7, float(left_kd), dtype=float)
        self.Kp_right = np.full(7, float(right_kp), dtype=float)
        self.Kd_right = np.full(7, float(right_kd), dtype=float)

        if right_sign is None:
            self.right_sign = np.ones(7, dtype=float)
        else:
            self.right_sign = _as_7d_vector(right_sign, "right_sign")

        ctrlrange = np.asarray(model.actuator_ctrlrange, dtype=float)
        if ctrlrange.ndim != 2 or ctrlrange.shape[1] != 2:
            raise ValueError("model.actuator_ctrlrange must have shape (nu, 2)")
        if ctrlrange.shape[0] < int(model.nu):
            raise ValueError("model.actuator_ctrlrange has fewer rows than model.nu")
        self.ctrl_min = ctrlrange[: int(model.nu), 0]
        self.ctrl_max = ctrlrange[: int(model.nu), 1]

    def compute(self, data, q_des_left: Sequence[float], q_des_right: Sequence[float]) -> np.ndarray:
        """
        Compute actuator torques for both arms.

        Returns a full control vector of shape (model.nu,).
        """

        q_des_left_vec = _as_7d_vector(q_des_left, "q_des_left")
        q_des_right_vec = _as_7d_vector(q_des_right, "q_des_right")

        qpos = np.asarray(data.qpos, dtype=float)
        qvel = np.asarray(data.qvel, dtype=float)
        qfrc_bias = np.asarray(data.qfrc_bias, dtype=float)

        q_left = qpos[self.left_joint_ids]
        qd_left = qvel[self.left_joint_ids]
        q_right = qpos[self.right_joint_ids]
        qd_right = qvel[self.right_joint_ids]

        tau_left = self.Kp_left * (q_des_left_vec - q_left) + self.Kd_left * (-qd_left)
        q_des_right_mirrored = self.right_sign * q_des_right_vec
        tau_right = self.Kp_right * (q_des_right_mirrored - q_right) + self.Kd_right * (-qd_right)

        tau_left += qfrc_bias[self.left_joint_ids]
        tau_right += qfrc_bias[self.right_joint_ids]

        tau = np.zeros(int(self.model.nu), dtype=float)
        tau[self.left_actuator_ids] = tau_left
        tau[self.right_actuator_ids] = tau_right

        np.clip(tau, self.ctrl_min, self.ctrl_max, out=tau)
        return tau
