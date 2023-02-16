sudo docker run --gpus all -ti -v ./datasets:/opt/monai/datasets/ --ipc=host --net=host --name real_hip_segmentation monailabel bash

sudo docker cp ./radiology real_hip_segmentation:/opt/monai/apps/radiology

monailabel start_server --app apps/radiology --studies datasets --conf models segmentation
