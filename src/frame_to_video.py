import json
import os

import cv2


def convert_images_to_video(image_dir, output_video, fps=5):
    """Converts a sequence of images in a directory to a video.

    Args:
        image_dir (str): Path to the directory containing images.
        output_video (str): Path to save the output video file (e.g., 'output.avi')
        fps (int, optional): Frames per second of the output video. Defaults to 30.
    """

    image_files = [
        img
        for img in os.listdir(image_dir)
        if not img.startswith("planner_snapshot_")
        and (img.endswith(".png") or img.endswith(".jpg"))
    ]
    image_files.sort()  # Ensure images are in correct order

    # Get dimensions from the first image
    frame = cv2.imread(os.path.join(image_dir, image_files[0]))
    height, width, layers = frame.shape

    # Define the video codec (you may need to experiment for compatibility)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Example: XVID codec

    video = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    for image in image_files:
        video.write(cv2.imread(os.path.join(image_dir, image)))

    # cv2.destroyAllWindows()
    video.release()
    print("Video conversion complete!")


if __name__ == "__main__":
    with open("datadump/results/eval_hssd/episode_final_coord.json", "r") as file:
        episodes = json.load(file)
    episode_ids = list(episodes.keys())
    base_image_dir = "datadump/episode_vis/eval_hssd/"  # Base directory to search in

    base_vid_dir = "datadump/episode_vid/eval_hssd/"  # base video directory
    os.makedirs(base_vid_dir)

    for episode_id in episode_ids:
        # Search for matching folder
        for folder in os.listdir(base_image_dir):
            if folder.endswith("_" + episode_id):
                image_dir = os.path.join(base_image_dir, folder)
                output_video = os.path.join(
                    base_vid_dir, "video_" + episode_id + ".mp4"
                )
                convert_images_to_video(image_dir, output_video)
                break  # Move on to the next episode_id once the folder is found
