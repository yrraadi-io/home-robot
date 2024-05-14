import gzip
import json

episodes = json.load(gzip.open("data/datasets/ovmm/val/custom_episodes.json.gz"))[
    "episodes"
]

with open("data/datasets/ovmm/val/custom_episodes.json", "w") as outfile:
    json.dump(episodes, outfile, indent=4)
