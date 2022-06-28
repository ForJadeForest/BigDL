#
# Copyright 2016 The BigDL Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# Most of the pytorch code is adapted from S0MNATHS's notebook for
# BrainMRI dataset.
# https://www.kaggle.com/s0mnaths/brain-mri-unet-pytorch/notebook
#

from __future__ import print_function
from torchvision.utils import make_grid
import matplotlib.pyplot as plt
import argparse
import glob
import os

import albumentations as A
import pandas as pd
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data
from bigdl.orca import init_orca_context, stop_orca_context
from bigdl.orca.learn.metrics import Accuracy
from bigdl.orca.learn.pytorch import Estimator
from sklearn.model_selection import train_test_split
from Unet import UNet
from dataset import *


def dataset(root_path):
    mask_files = glob.glob(root_path + '/*/*_mask*')
    image_files = [file.replace('_mask', '') for file in mask_files]
    files_df = pd.DataFrame({"image_path": image_files,
                             "mask_path": mask_files,
                             "diagnosis": [diagnosis(x) for x in mask_files]})
    train_df, test_df = train_test_split(files_df, stratify=files_df['diagnosis'], test_size=0.15, random_state=0)
    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    return train_df, test_df


def dice_coef_metric(pred, label):
    intersection = 2.0 * (pred * label).sum()
    union = pred.sum() + label.sum()
    if pred.sum() == 0 and label.sum() == 0:
        return 1.
    return intersection / union


def dice_coef_loss(pred, label):
    smooth = 1.0
    intersection = 2.0 * (pred * label).sum() + smooth
    union = pred.sum() + label.sum() + smooth
    return 1 - (intersection / union)


def bce_dice_loss(pred, label):
    dice_loss = dice_coef_loss(pred, label)
    bce_loss = nn.BCELoss()(pred, label)
    return dice_loss + bce_loss


def loss_creator(config):
    return bce_dice_loss


def show_batch(dl):
    for images, masks in dl:
        fig1, ax1 = plt.subplots(figsize=(24, 24))
        ax1.set_xticks([])
        ax1.set_yticks([])
        denorm_images = denormalize(images)
        ax1.imshow(make_grid(denorm_images[:13], nrow=13).permute(1, 2, 0).clamp(0, 1))
        fig2, ax2 = plt.subplots(figsize=(24, 24))
        ax2.set_xticks([])
        ax2.set_yticks([])
        ax2.imshow(make_grid(masks[:13], nrow=13).permute(1, 2, 0).clamp(0, 1))
        break


def train_loader_creator(config, batch_size):
    train_transform = A.Compose([
        A.Resize(width=128, height=128, p=1.0),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.ShiftScaleRotate(shift_limit=0.01, scale_limit=0.04, rotate_limit=0, p=0.25),
    ])

    train_ds = BrainDataset(config['train'], train_transform)
    trainloader = torch.utils.data.DataLoader(train_ds, batch_size=batch_size,
                                              shuffle=True, num_workers=0)
    return trainloader


def test_loader_creator(config, batch_size):
    test_transform = A.Compose([
        A.Resize(width=128, height=128, p=1.0)
    ])

    test_ds = BrainDataset(config['test'], test_transform)
    testloader = torch.utils.data.DataLoader(test_ds, batch_size=batch_size,
                                             shuffle=False, num_workers=0)
    return testloader


def model_creator(config):
    net = UNet(3, 1)
    return net


def optim_creator(model, config):
    optimizer = optim.Adam(model.parameters(),
                           lr=config.get("lr", 0.001),
                           )
    return optimizer


def denormalize(images):
    means = torch.tensor([0.485, 0.456, 0.406]).reshape(1, 3, 1, 1)
    stds = torch.tensor([0.229, 0.224, 0.225]).reshape(1, 3, 1, 1)
    return images * stds + means


parser = argparse.ArgumentParser(description='PyTorch brainMRI Example')
parser.add_argument('--cluster_mode', type=str, default="local",
                    help='The cluster mode, such as local, yarn-client, spark-submit.')
parser.add_argument('--backend', type=str, default="torch_distributed",
                    help='The backend of PyTorch Estimator; torch_distributed and spark are supported')
parser.add_argument('--batch_size', type=int, default=64, help='The training batch size')
parser.add_argument('--epochs', type=int, default=2, help='The number of epochs to train for')
parser.add_argument('--data_dir', type=str, default='./kaggle_3m', help='the path of the dataset')
parser.add_argument('--additional_archive', type=str, default="kaggle_3m.zip#kaggle_3m", help='the zip dataset')
parser.add_argument('--memory', type=str, default="4g", help="the memory allocated for each node")
parser.add_argument('--model_dir', type=str, default='file://' + os.getcwd(),
                    help="the model save dir when use spark backend")
args = parser.parse_args()

train_df, test_df = dataset(args.data_dir)

if args.cluster_mode == "local":
    init_orca_context(memory=args.memory)
elif args.cluster_mode.startswith('yarn'):
    config = {}
    if args.backend == 'spark':
        config = {'spark.executorEnv.ARROW_LIBHDFS_DIR': '/opt/cloudera/parcels/CDH-5.15.2-1.cdh5.15.2.p0.3/lib64'}
    init_orca_context(cluster_mode="yarn-client", cores=2, num_nodes=2, additional_archive=args.additional_archive,
                      extra_python_lib='dataset.py,Unet.py', num_executors=2, memory=args.memory, conf=config)
elif args.cluster_mode == "spark-submit":
    init_orca_context(cluster_mode="spark-submit")
else:
    raise NotImplementedError("Only local, yarn-client, and spark-submit are supported as the cluster_mode,"
                              " but got {}".format(args.cluster_mode))

criterion = nn.CrossEntropyLoss()
batch_size = args.batch_size
epochs = args.epochs
train_loader = train_loader_creator(config={"train": train_df}, batch_size=batch_size)

# plot some random training images
show_batch(train_loader)

if args.backend in ["torch_distributed", "spark"]:
    config = {
        'lf': 1e-3,
        'train': train_df,
        'test': test_df
    }
    orca_estimator = Estimator.from_torch(model=model_creator,
                                          optimizer=optim_creator,
                                          loss=loss_creator,
                                          model_dir=args.model_dir,
                                          metrics=[Accuracy(), dice_coef_metric],
                                          backend=args.backend,
                                          config=config,
                                          use_tqdm=True
                                          )

    orca_estimator.fit(data=train_loader_creator, epochs=args.epochs, batch_size=batch_size)
    res = orca_estimator.evaluate(data=test_loader_creator, batch_size=batch_size)
    print(res)
else:
    raise NotImplementedError("Only torch_distributed and spark are supported as the backend,"
                              " but got {}".format(args.backend))

stop_orca_context()
