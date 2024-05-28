import gzip
import json

# load episodes
episodes_obj = json.load(gzip.open("data/datasets/ovmm/val/episodes.json.gz"))
episodes = episodes_obj["episodes"]

# load new start coordinates
with open("datadump/results/eval_hssd/episode_final_coord.json", "r") as file:
    episode_coord = json.load(file)

# new custom episode dump
found_episodes = []
new_episodes = []

for episode in episodes:
    id = episode["episode_id"]
    if id in episode_coord:
        episode["start_position"] = episode_coord[id]["position"]
        episode["start_rotation"] = episode_coord[id]["rotation"]
        new_episodes.append(episode)
        if episode_coord[id]["found_goal"]:
            found_episodes.append(episode)

episodes_obj["episodes"] = new_episodes
with gzip.open("data/datasets/ovmm/val/custom_episodes.json.gz", "wt") as outfile:
    json.dump(episodes_obj, outfile)
    
episodes_obj["episodes"] = found_episodes
with gzip.open("data/datasets/ovmm/val/found_episodes.json.gz", "wt") as outfile:
    json.dump(episodes_obj, outfile)
