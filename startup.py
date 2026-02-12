import mujoco
import mujoco.viewer
import numpy as np

from PID_Control import JointSpacePDController  # adjust filename if needed


# -------------------------
# Load MuJoCo model
# -------------------------
model = mujoco.MjModel.from_xml_path("aloha.xml")  # <-- change filename
data = mujoco.MjData(model)

# -------------------------
# Create controller
# -------------------------
controller = JointSpacePDController(model)

# -------------------------
# Simulation settings
# -------------------------
sim_time = 1000.0  # seconds
dt = model.opt.timestep
steps = int(sim_time / dt)

# -------------------------
# Initial desired positions
# -------------------------
q_des_left = np.zeros(7)
q_des_right = np.zeros(7)

# Example test:
# Left shoulder +0.3 rad
# Right shoulder +0.3 rad (will be mirrored internally if right_sign changed)
q_des_left[0] = 0.3
q_des_right[0] = 0.3

# -------------------------
# Run simulation
# -------------------------
with mujoco.viewer.launch_passive(model, data) as viewer:

    for step in range(steps):

        # Compute torques
        tau = controller.compute(data, q_des_left, q_des_right)

        # Apply torques to actuators
        data.ctrl[:14] = tau

        # Step simulation
        mujoco.mj_step(model, data)

        viewer.sync()
