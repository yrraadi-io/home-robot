import gzip
import json

episodes = json.load(gzip.open("data/datasets/ovmm/val/episodes.json.gz"))["episodes"]

with open("episode_view2.json", "w") as outfile:
    json.dump(episodes, outfile, indent=4)
