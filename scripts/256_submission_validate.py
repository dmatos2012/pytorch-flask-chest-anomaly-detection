# -*- coding: utf-8 -*-
"""256_submission_validate.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RItayM3mL7vfeyHMjWbeu2LOhBK4DlUD
"""

import os
import sys
from torch.utils.data import DataLoader
from torchvision.transforms import functional as F
from input256_p100_train_effnet import XRayDataset, get_transform,input_config, config, Evaluator

from effdet import create_model, unwrap_bench, create_loader,create_model_from_config,  DetBenchTrain, EfficientDet, create_evaluator
from effdet.config import get_efficientdet_config

from effdet.efficientdet import HeadNet
from effdet.data import resolve_input_config

from timm.optim import create_optimizer
from timm.scheduler import create_scheduler

import time
import torch
import numpy as np 
import torch.nn.parallel
from contextlib import suppress

from effdet import create_model, create_evaluator, create_dataset, create_loader
from effdet.data import resolve_input_config
from timm.utils import AverageMeter, setup_default_logging
from timm.models.layers import set_layer_config

import pandas as pd


# %cd "/content"

# Commented out IPython magic to ensure Python compatibility.
# Need to recreate same folder structure as the traineffdet so it can find the items and pictures 
# and csv
# %cd "/content"
# !unzip -q /content/drive/MyDrive/kaggle/chest_xray_detection/chest_xray_1024.zip
# !unzip -q /content/drive/MyDrive/kaggle/chest_xray_detection/chest_xray_256.zip -d /content/vinbigdata

# root = os.getcwd()
# train_dataset, validation_dataset = create_dataset(root)
# # print(validation_dataset.__getitem__(0))


root = os.getcwd()
validation_dataset =  XRayDataset(root, get_transform(train = False), split="test")
batch_size = 1
# img, target = validation_dataset.__getitem__(1)

def collate_fn(batch):
    return tuple(zip(*batch))

loader = DataLoader(
    validation_dataset,
    batch_size= batch_size,
    shuffle=False,
    num_workers=4,
    drop_last=False,
    collate_fn=collate_fn
)


model_name =  "tf_efficientdet_d4"
num_classes = 15
pretrained = False
checkpoint_path = "./output/0325_training_6_kaggle/checkpoint-16.pth.tar" #  from exp6
use_ema = False
redundant_bias = None

#soft nms not in this particular library. 


base_config = get_efficientdet_config(config.model.model)
base_config.image_size = (256,256) #override the [512,512]
with set_layer_config(scriptable=False):
  #base_config.norm_kwargs=dict(eps=.001, momentum=.01)

  bench = create_model_from_config(base_config, bench_task='predict', pretrained = pretrained,
                                  num_classes = num_classes, redundant_bias = None,
                                  checkpoint_path=checkpoint_path, 
                                  checkpoint_ema=use_ema)
  
# with set_layer_config(scriptable=False):
#         bench = create_model(
#             model_name,
#             bench_task='predict',
#             num_classes=num_classes,
#             pretrained=pretrained,
#             redundant_bias=redundant_bias,
#             checkpoint_path=checkpoint_path,
#             checkpoint_ema=use_ema,
#         )
# basically copy of the train_effdet model 

model_config = bench.config
# model_config.image_size = (1024,1024) # is this the problem?it says 512,512n 
param_count = sum([m.numel() for m in bench.parameters()])
print('Model %s created, param count: %d' % (model_name, param_count))
bench  = bench.cuda()
amp_autocass = suppress
native_amp = True
amp_autocast = torch.cuda.amp.autocast
print("Using native Torch AMP. Validating in mixed precision.")

num_workers = 2
log_freq = 10

# loader = create_loader(
#         validation_dataset,
#         input_size=input_config['input_size'],
#         batch_size=config.model.batch_size,
#         use_prefetcher=True,
#         interpolation=input_config['interpolation'],
#         fill_color=input_config['fill_color'],
#         mean=input_config['mean'],
#         std=input_config['std'],
#         num_workers=num_workers,
#         pin_mem=False)


#create evaluator. DOuble check since this is the part that is wrong, coco api and stuff
# evaluator = Evaluator(validation_dataset, distributed= False, pred_yxyx = False) #False? who knows. 

def format_img_result(bboxes, score, label):
  batch_res_str = []

  for idx in range(bboxes.shape[0]):
    bbox_str = " ".join(map(str, bboxes[idx,:]))
    res_str = str(int(label[idx])) +  " " + str(score[idx]) + " " + bbox_str
    batch_res_str.append(res_str) 
  pred_str = " ".join(batch_res_str)
  return pred_str


def rescale_bboxes(bboxes, target):
  img_width = target['img_info'][0]
  img_height = target['img_info'][1]
  #1,4
  def_img_size = 256
  x_scale = img_width/def_img_size
  y_scale = img_height/def_img_size
  
  if not np.array_equal(bboxes, np.array([[0,0,1,1]])):
    bboxes[:,[0,2]] = bboxes[:,[0,2]] * x_scale
    bboxes[:,[1,3]] = bboxes[:,[1,3]] * y_scale
  return bboxes

def get_prediction(score_threshold, target, batch_output):
  batch_output = batch_output.cpu().numpy()
  for idx in range(batch_output.shape[0]):
      # print("target", target[idx])
    output = batch_output[idx,:,:]
    bboxes = output[:,:4]
    score = output[:,-2]
    label = output[:,-1]
    indices = np.where(score > score_threshold)
    label = label[indices]
    bboxes = bboxes[indices]
    score = score[indices]
    if indices[0].size == 0 or 14 in label: #empty or "no finding"
      bboxes = np.array([0,0,1,1], ndmin=2)
      #emptyscore = np.array([1])
      label = np.array([14]) #label[indices]

    bboxes = rescale_bboxes(bboxes, target[idx])
  return bboxes, label, score


bench.eval()
batch_time = AverageMeter()
end = time.time()
last_idx = len(loader) - 1
score_threshold = 0.20 #0.35 the first time. #0.60 highest
df_res = []
df_img_id = []
with torch.no_grad():
  for i, (input, target) in enumerate(loader):
    print(f'{i} out of {len(loader)}')
    print("input before", input[0].shape)
    res = {}
    # print("target", target)
    input = torch.stack(input).cuda().float()
    print("input", input.shape)
    # print("input", input.shape)
    # print(input.shape)
    with amp_autocast():
      batch_output = bench(input)
      print(get_prediction( score_threshold, target, batch_output))


 







        
      
    


##PREDICTING LOTS OF CLASS 10 UNFORTUNATELY. NO 14 CLASS. SO BAD THO. 




#img_scale, img_size keys missing in dictionary for target. fix that
# also add filename(to target), so that I know what I am evaluating
# to validate that filename maps to correct bbox coordinates. 

# img_size = input[0].shape[-2:]
# target["img_scale"] = torch.tensor([1.0] * config.model.batch_size, dtype=torch.float).to('cuda:0')
# target["img_size"] = torch.tensor([img_size] * config.model.batch_size, dtype=torch.float).to('cuda:0')

 # output shape [x_min, y_min, x_max, y_max, score, class]

# Draw sample predictions
# from google.colab.patches import cv2_imshow
# import cv2
# from PIL import Image
# from IPython.display import display # to display images
# import matplotlib.pyplot as plt
# import numpy as np 
# img, target = validation_dataset.__getitem__(75)
# filename = target['filename']
# print(filename)
# img = Image.fromarray(img.mul(255).permute(1, 2, 0).byte().numpy())
# img = np.array(img) 
# img_original = cv2.imread("0792bb20718b8006f78094ae449c3c96.png")
# # Convert RGB to BGR 
# img = img[:, :, ::-1].copy() 
# start_point = (int(159.119),int(242.967))
# end_point = (int(917.1665), int(1800.1061))
# # display(img)
# # Blue color in BGR 
# color = (255, 0, 0) 
# # Line thickness of 2 px 
# thickness = 2
# image = cv2.rectangle(img_original, start_point, end_point, color, thickness) 
# cv2_imshow(image)
  

#80.582535 104.1434   464.47998  771.58167
# 159.11903  242.96738  917.1665  1800.1061

