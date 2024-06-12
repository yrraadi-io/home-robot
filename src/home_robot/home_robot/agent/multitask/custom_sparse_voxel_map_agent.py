# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Creates a CustomSparseVoxelMap of a scene and evaluates it on that scene
"""
import json
import logging
from enum import IntEnum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import Tensor
from tqdm import tqdm

from home_robot.core.interfaces import Observations
from home_robot.datasets.scannet import ScanNetDataset
from home_robot.mapping.instance import Instance
from home_robot.mapping.voxel import SparseVoxelMap
from home_robot.perception import OvmmPerception
from home_robot.perception.constants import RearrangeDETICCategories

logger = logging.getLogger(__name__)


class SemanticVocab(IntEnum):
    FULL = auto()
    SIMPLE = auto()
    ALL = auto()


class CustomSparseVoxelMapAgent:
    """Simple class to collect RGB, Depth, and Pose information for building 3d spatial-semantic
    maps for the robot. Needs to subscribe to:
    - color images
    - depth images
    - camera info
    - joint states/head camera pose
    - base pose (relative to world frame)

    - Add option to cache Instance Segmentation + Pixel features
    This is an example collecting the data; not necessarily the way you should do it.
    """

    def __init__(
        self,
        semantic_sensor: Optional[OvmmPerception] = None,
        voxel_map: Optional[SparseVoxelMap] = SparseVoxelMap(feature_dim=3, resolution=0.03),
        visualize_planner=False,
        device="cpu",
        cache_dir: Optional[Union[Path, str]] = None,
    ):
        self.device = device
        self.semantic_sensor = semantic_sensor
        self.voxel_map = voxel_map
        self.visualize_planner = visualize_planner
        self.cache_dir = cache_dir

    def reset(self):
        self.voxel_map.reset()

    ##############################################
    # Add new observations
    ##############################################
    def step(self, obs: Observations, visualize_map=False):
        """Step the collector. Get a single observation of the world. Remove bad points, such as
        those from too far or too near the camera."""
        instance_image = obs.instance
        instance_classes = obs.task_observations["instance_classes"]
        instance_scores = obs.task_observations["instance_scores"]

        self.voxel_map.add(
            rgb=torch.from_numpy(obs.rgb).float() / 255.0,
            depth=obs.depth,
            feats=obs.task_observations.get("features", None),
            camera_K=obs.camera_K,
            camera_pose=obs.camera_pose,  # scene_obs['axis_align_mats'][i] @ scene_obs['poses'][i]
            instance_image=instance_image,
            instance_classes=instance_classes,
            instance_scores=instance_scores,
            obs=obs,
        )

        if visualize_map:
            # Now draw 2d
            self.voxel_map.get_2d_map(debug=True)

    def step_trajectory(
        self, obs_list: Sequence[Observations], cache_key: Optional[str] = None
    ):
        """Tkes a list of observations and adds them all to the instance map"""
        if cache_key is not None:
            # load from cache
            assert self.cache_dir is not None
            raise NotImplementedError
        else:
            for i, obs in enumerate(obs_list):
                self.step(obs)
            if self.cache_dir is not None:
                # Save to cache
                raise NotImplementedError
        logger.debug(f"Found {len(self.voxel_map.get_instances())} instances")

    ##############################################
    # Language queries that return instances
    ##############################################
    def set_vocabulary(self, vocabulary: Dict[int, str]):
        vocabulary = RearrangeDETICCategories(vocabulary)
        self.semantic_sensor.update_vocabulary_list(vocabulary, SemanticVocab.SIMPLE)
        self.semantic_sensor.set_vocabulary(SemanticVocab.SIMPLE)
        return self.semantic_sensor.current_vocabulary

    def get_instances_for_query(
        self, text_query: str, method: str = "class_match", return_scores: bool = False
    ) -> List[Instance]:
        instances = self.voxel_map.get_instances()

        if method == "class_match":
            assert (
                text_query in self.semantic_sensor.name_to_seg_id
            ), f"{text_query} not in semantic_sensor vocabulary (current vocab: {self.semantic_sensor.current_vocabulary_id})"
            query_class_id = self.semantic_sensor.name_to_seg_id[text_query]
            instances = [
                inst for inst in instances if inst.category_id == query_class_id
            ]
            scores = [inst.score for inst in instances]
        elif method == "text_image_encoder":
            assert (
                self.voxel_map.encoder is not None
            ), 'Getting queries using "text_image_encoder" method requries using an encoder, but voxel_map.encoder is None'
            encoder = self.voxel_map.encoder
            text_embed = encoder.encode_text("chair")
            text_embed = text_embed / text_embed.norm(dim=-1)
            inst_embeddings = [
                inst.get_image_embedding(aggregation_method="max") for inst in instances
            ]
            scores = [
                (text_embed * image_embed.to(text_embed.device)).sum(dim=-1).max()
                for image_embed in inst_embeddings
            ]
        else:
            raise NotImplementedError(f"Unknown method type {method}")

        if return_scores:
            return instances, scores
        else:
            return instances

    def build_scene_and_get_instances_for_queries(
        self, scene_obs: Dict[str, Any], queries: Sequence[str], reset: bool = True
    ) -> Dict[str, List[Instance]]:
        """_summary_

        Args:
            scene_obs (Dict[str, Any]): Contains
                - Images
                - Depths
                - Poses
                - Intrinsics
                - scan_name -- str that could be used for caching (but we probably also want to pass in dataset or sth in case we change resoluton, frame_skip, etc)
            queries (Sequence[str]): Text queries, processed independently

        Returns:
            Dict[str, List[Instance]]: mapping queries to instances
        """
        # Build scene representation
        obs_list = []
        for i in range(len(scene_obs["images"])):
            obs = Observations(
                gps=None,
                compass=None,
                rgb=scene_obs["images"][i] * 255,
                depth=scene_obs["depths"][i],
                semantic=None,
                instance=None,  # These could be cached
                # Pose of the camera in world coordinates
                camera_pose=scene_obs["poses"][i],
                camera_K=scene_obs["intrinsics"][i],
                task_observations={
                    # "features": scene_obs["images"][i],
                },
            )
            obs_list.append(obs)
        self.step_trajectory(obs_list)
        self.voxel_map.postprocess_instances()

        # Get query results
        instances_dict = {}
        for class_name in queries:
            instances_dict[class_name] = self.get_instances_for_query(class_name)
        if reset:
            self.reset()
        return instances_dict

    ##############################################
    # 2D map projections for planning
    ##############################################
    def get_2d_map(self):
        """Get 2d obstacle map for low level motion planning and frontier-based exploration"""
        return self.voxel_map.get_2d_map()

    def show(self) -> Tuple[np.ndarray, np.ndarray]:
        """Display the aggregated point cloud."""
        return self.voxel_map.show(
            instances=True,
            height=1000,
            boxes_plot_together=False,
            # boxes_name_int_to_display_name_dict=dict(
            #     enumerate(self.metadata.thing_classes)
            # ),
            backend="pytorch3d",
        )

    ##############################################
    # IoU calculation
    ##############################################
    def evaluate_iou(self):
        """Get ground truth features, predicted features and calculate IoU"""
        # Capture features
        features = self.voxel_map.get_features()
        predicted_mask = features[:, 0] == 1
        gt_mask = features[:, 1] == 1

        # calculate IoU
        intersection = torch.logical_and(gt_mask, predicted_mask).sum().item()
        union = torch.logical_or(gt_mask, predicted_mask).sum().item()

        # Handle potential division by zero
        iou = intersection / union if union > 0 else 0.0
        return iou
    
    ##############################################
    # Logging and debugging
    ##############################################
    def export_voxel_labels_to_json(self, filename: str):
        voxel_pcd = self.voxel_map.get_voxelized_pointcloud()
        with open(filename, 'w') as f:
            json.dump(voxel_pcd._voxel_labels, f, indent=4)
