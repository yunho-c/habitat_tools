import numpy as np
from modeling.utils.baseline_utils import (
    read_sem_map_npy,
    pose_to_coords,
    save_occ_map_through_plt,
)
import habitat
from core import cfg

# specify on which scene you want to build the map
scene = "2t7WUuJeko7"
height = 0.16325

semantic_map_folder = "output/semantic_map"

# after testing, using 8 angles is most efficient
theta_lst = [0]
cell_size = cfg.SEM_MAP.CELL_SIZE

# === initialize a grid ===
x = np.arange(-cfg.SEM_MAP.WORLD_SIZE, cfg.SEM_MAP.WORLD_SIZE, cell_size)
z = np.arange(-cfg.SEM_MAP.WORLD_SIZE, cfg.SEM_MAP.WORLD_SIZE, cell_size)
xv, zv = np.meshgrid(x, z)
grid_H, grid_W = zv.shape

# === initialize the habitat environment ===
config = habitat.get_config(config_paths="configs/habitat_env/build_map_mp3d.yaml")
config.defrost()
config.SIMULATOR.SCENE = f"data/scene_datasets/mp3d/{scene}/{scene}.glb"
config.SIMULATOR.SCENE_DATASET = (
    "data/scene_datasets/mp3d/mp3d_annotated_basis.scene_dataset_config.json"
)
config.freeze()

env = habitat.sims.make_sim(config.SIMULATOR.TYPE, config=config.SIMULATOR)
env.reset()

# load the pre-built semantic map
sem_map_npy = np.load(
    f"{semantic_map_folder}/{scene}/BEV_semantic_map.npy", allow_pickle=True
).item()
map_data = read_sem_map_npy(sem_map_npy)

# initialize the occupancy grid
occ_map = np.zeros((grid_H, grid_W), dtype=int)

# === traverse the environment ===
count_ = 0

for grid_z in range(grid_H):
    for grid_x in range(grid_W):
        x = xv[grid_z, grid_x] + cell_size / 2.0
        z = zv[grid_z, grid_x] + cell_size / 2.0
        y = height

        agent_pos = np.array([x, y, z])
        flag_nav = env.is_navigable(agent_pos)

        if flag_nav:
            x = xv[grid_z, grid_x] + cell_size / 2.0
            z = zv[grid_z, grid_x] + cell_size / 2.0
            # convert environment pose to map coordinates
            x_coord, z_coord = pose_to_coords((x, z), map_data, flag_cropped=False)
            occ_map[z_coord, x_coord] = 1

# cut occupancy map and make it same size as the semantic map
coords_range = map_data["coords_range"]
pose_range = map_data["pose_range"]
wh = map_data["wh"]
occ_map = occ_map[
    coords_range[1] : coords_range[3] + 1, coords_range[0] : coords_range[2] + 1
]

# save the final results
map_dict = {}
map_dict["occupancy"] = occ_map
map_dict["min_x"] = coords_range[0]
map_dict["max_x"] = coords_range[2]
map_dict["min_z"] = coords_range[1]
map_dict["max_z"] = coords_range[3]
map_dict["min_X"] = pose_range[0]
map_dict["max_X"] = pose_range[2]
map_dict["min_Z"] = pose_range[1]
map_dict["max_Z"] = pose_range[3]
map_dict["W"] = wh[0]
map_dict["H"] = wh[1]
np.save(f"{semantic_map_folder}/{scene}/BEV_occupancy_map.npy", map_dict)

# save the final color image
save_occ_map_through_plt(occ_map, f"{semantic_map_folder}/{scene}/occ_map.jpg")

print("**********************finished building the occ map!")

env.close()
