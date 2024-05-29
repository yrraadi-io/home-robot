import gzip
import json

# Function to save episodes
def save_custom_episodes(confidence_threshold):
    # load episodes
    episodes_obj = json.load(gzip.open("data/datasets/ovmm/val/episodes.json.gz"))
    episodes = episodes_obj["episodes"]

    # load new start coordinates
    filename = f"datadump/results/eval_hssd/episode_final_coord_{confidence_threshold}.json"
    with open(filename, "r") as file:
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

    if len(new_episodes) > 0:
        episodes_obj["episodes"] = new_episodes
        custom_episodes_filename = f"data/datasets/ovmm/val/custom_episodes_{confidence_threshold}.json.gz"
        with gzip.open(custom_episodes_filename, "wt") as outfile:
            json.dump(episodes_obj, outfile)

    if len(found_episodes) > 0:
        episodes_obj["episodes"] = found_episodes
        found_episodes_filename = f"data/datasets/ovmm/val/found_episodes_{confidence_threshold}.json.gz"
        with gzip.open(found_episodes_filename, "wt") as outfile:
            json.dump(episodes_obj, outfile)

# User input for confidence threshold
confidence_threshold = input("Enter the confidence threshold (e.g., 0.75): ")
save_custom_episodes(confidence_threshold)
