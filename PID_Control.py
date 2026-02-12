import mujoco
import numpy as np

class JointSpacePDController:
    def __init__(self, model):

        self.model = model

        # ----- Joint indexing -----
        self.left_ids  = np.arange(0, 7)
        self.right_ids = np.arange(7, 14)

        assert len(self.left_ids) == 7
        assert len(self.right_ids) == 7

        # ----- Gains (separate per arm) -----
        self.Kp_left  = np.ones(7) * 20.0
        self.Kd_left  = np.ones(7) * 10.0

        self.Kp_right = np.ones(7) * 20.0
        self.Kd_right = np.ones(7) * 10.0

        # ----- Optional mirror signs for right arm -----
        # Adjust signs if needed after testing
        self.right_sign = np.ones(7)
        # Example if mirroring required:
        # self.right_sign = np.array([-1, 1, -1, 1, 1, -1, 1])

        # ----- Actuator torque limits -----
        self.ctrl_min = model.actuator_ctrlrange[:, 0]
        self.ctrl_max = model.actuator_ctrlrange[:, 1]

    def compute(self, data, q_des_left, q_des_right):
        """
        Parameters
        ----------
        data : mujoco.MjData
        q_des_left  : np.ndarray (7,)
        q_des_right : np.ndarray (7,)

        Returns
        -------
        tau : np.ndarray (14,)
        """

        # Current state
        q  = data.qpos
        qd = data.qvel

        # Allocate torque vector
        tau = np.zeros(14)

        # =========================
        # LEFT ARM CONTROL
        # =========================
        q_left  = q[self.left_ids]
        qd_left = qd[self.left_ids]

        pos_error_left = q_des_left - q_left
        vel_error_left = -qd_left

        tau_left = (
            self.Kp_left * pos_error_left +
            self.Kd_left * vel_error_left
        )

        tau[self.left_ids] = tau_left

        # =========================
        # RIGHT ARM CONTROL
        # =========================
        q_right  = q[self.right_ids]
        qd_right = qd[self.right_ids]

        # Apply mirror sign to desired position
        q_des_right_mirrored = self.right_sign * q_des_right

        pos_error_right = q_des_right_mirrored - q_right
        vel_error_right = -qd_right

        tau_right = (
            self.Kp_right * pos_error_right +
            self.Kd_right * vel_error_right
        )

        tau[self.right_ids] = tau_right

        # =========================
        # Gravity + Coriolis Compensation
        # =========================
        tau += data.qfrc_bias[:14]

        # =========================
        # Clip to actuator limits
        # =========================
        tau = np.clip(tau, self.ctrl_min[:14], self.ctrl_max[:14])

        return tau
