import gzip
import json

episodes_obj = json.load(gzip.open("data/datasets/ovmm/val/episodes.json.gz"))
episodes = episodes_obj["episodes"]

with open("datadump/results/eval_hssd/episode_final_coord.json", "r") as file:
    episode_coord = json.load(file)

for episode in episodes:
    if episode["episode_id"] == "10":
        episode["start_position"] = episode_coord["10"]["position"]
        episode["start_rotation"] = episode_coord["10"]["rotation"]

episodes_obj["episodes"] = episodes

with open("data/datasets/ovmm/val/custom_episodes.json", "w") as outfile:
    json.dump(episodes_obj, outfile, indent=4)
