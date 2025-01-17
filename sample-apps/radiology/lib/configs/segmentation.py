# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from typing import Any, Dict, Optional, Union

import lib.infers
import lib.trainers
from monai.networks.nets import SegResNet
from monai.utils import optional_import

from monailabel.interfaces.config import TaskConfig
from monailabel.interfaces.tasks.infer_v2 import InferTask
from monailabel.interfaces.tasks.train import TrainTask
from monailabel.utils.others.generic import download_file, strtobool

_, has_cp = optional_import("cupy")
_, has_cucim = optional_import("cucim")

logger = logging.getLogger(__name__)


class Segmentation(TaskConfig):
    def init(self, name: str, model_dir: str, conf: Dict[str, str], planner: Any, **kwargs):
        super().init(name, model_dir, conf, planner, **kwargs)

        # Labels - http://xrayhead.com/theatlas.php?id=thigh
        label_list = [
                    # Anterior thigh muscle (thigh to extend the leg at the knee joint)
                    "sartorius muscle",
                    "rectus femoris muscle",
                    "vastus lateralis",
                    "vastus intermedius",
                    "vastus medialis",
                    "articularis genus muscle",

                    # Medial thigh muscle (inner side of the thigh)
                    "adductor longus",
                    "adductor brevis",
                    "adductor magnus",
                    "adductor minimus",
                    "gracilis muscle",
                    "pectineus",

                    # Gluteal region (area of the body that includes the buttocks, hips and surrounding muscles)
                    "gluteus maximus",
                    "gluteus medius",
                    "gluteus minimus",
                    "tensor fascia lata muscle",
                    "piriformis muscle",
                    "obturator internus muscle",
                    "obturator externus muscle",
                    "superior gemellus",
                    "inferior gemellus",
                    "quadratus femoris",

                    # Posterior femoral muscle (the back of the thigh, also known ad the hamstring muscles)
                    "semitendinous muscle",
                    "semimembranosus muscle",
                    "biceps femoris",

                    # Else
                    "iliacus muscle",
                    "iliopsoas",
                    "abdominal oblique muscle",
                    "mulifidus muscle",
                    "rectus abdominus muscle",

                    # Other tissues
                    "femoral",
                    "iliac",
                    "background"


                    # "iliacus muscle",
                    # "sartorius muscle",
                    # "obturator internal muscle",
                    # "obturator externus muscle",
                    # "abdominal oblique muscle",
                    # "psoas muscle",
                    # "iliopsoas",
                    # "pectineus muscle",
                    # "tensor fascia lata muscle",
                    # "piriformis muscle",
                    # "mulifidus muscle",
                    # "rectus abdominus muscle",
                    # "rectus femoris muscle",
                    # "sartorius muscle",
                    # "vastus lateralis",
                    # "vastus intermedius",
                    # "vastus medialis muscle",
                    # "adducter longus",
                    # "adductor brevis",
                    # "adductor magnus",
                    # "gracilis muscle",
                    # "semitendinosus muscle",
                    # "semimembranosus muscle",
                    # "biceps femoris(long head)",
                    # "biceps femoris(short head)",
                    # "gluteus maximus",
                    # "gluteus medius",
                    # "gluteus minimus"
                    ]
        self.labels = {key:idx for idx, key in enumerate(label_list)}
        # self.labels = {
            # "spleen": 1,
            # "kidney_right": 2,
            # "kidney_left": 3,
            # "gallbladder": 4,
            # "liver": 5,
            # "stomach": 6,
            # "aorta": 7,
            # "inferior_vena_cava": 8,
            # "portal_vein_and_splenic_vein": 9,
            # "pancreas": 10,
            # "adrenal_gland_right": 11,
            # "adrenal_gland_left": 12,
            # "lung_upper_lobe_left": 13,
            # "lung_lower_lobe_left": 14,
            # "lung_upper_lobe_right": 15,
            # "lung_middle_lobe_right": 16,
            # "lung_lower_lobe_right": 17,
            # "esophagus": 42,
            # "trachea": 43,
            # "heart_myocardium": 44,
            # "heart_atrium_left": 45,
            # "heart_ventricle_left": 46,
            # "heart_atrium_right": 47,
            # "heart_ventricle_right": 48,
            # "pulmonary_artery": 49,
        # }

        # Model Files
        self.path = [
            os.path.join(self.model_dir, f"pretrained_{name}.pt"),  # pretrained
            os.path.join(self.model_dir, f"{name}.pt"),  # published
        ]

        # Download PreTrained Model
        if strtobool(self.conf.get("use_pretrained_model", "true")):
            url = f"{self.conf.get('pretrained_path', self.PRE_TRAINED_PATH)}"
            url = f"{url}/radiology_segmentation_segresnet_multilabel.pt"
            download_file(url, self.path[0])

        self.target_spacing = (1.5, 1.5, 1.5)  # target space for image
        # Setting ROI size - This is for the image padding
        self.roi_size = (96, 96, 96)

        # Network
        self.network = SegResNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=len(self.labels) + 1,  # labels plus background,
            init_filters=32,
            blocks_down=(1, 2, 2, 4),
            blocks_up=(1, 1, 1),
            dropout_prob=0.2,
        )

    def infer(self) -> Union[InferTask, Dict[str, InferTask]]:
        task: InferTask = lib.infers.Segmentation(
            path=self.path,
            network=self.network,
            roi_size=self.roi_size,
            target_spacing=self.target_spacing,
            labels=self.labels,
            preload=strtobool(self.conf.get("preload", "false")),
            config={"largest_cc": True if has_cp and has_cucim else False},
        )
        return task

    def trainer(self) -> Optional[TrainTask]:
        output_dir = os.path.join(self.model_dir, self.name)
        load_path = self.path[0] if os.path.exists(self.path[0]) else self.path[1]

        task: TrainTask = lib.trainers.Segmentation(
            model_dir=output_dir,
            network=self.network,
            roi_size=self.roi_size,
            target_spacing=self.target_spacing,
            load_path=load_path,
            publish_path=self.path[1],
            description="Train Segmentation Model",
            labels=self.labels,
        )
        return task
