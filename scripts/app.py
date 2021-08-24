import os
import base64
from torchvision.transforms import functional as F
from PIL import Image
from effdet import create_model_from_config
from effdet.config import get_efficientdet_config
import yaml
from easydict import EasyDict
from pathlib import Path

import torchvision.transforms as transforms

import io
import torch
import numpy as np 
import torch.nn.parallel
from contextlib import suppress
from effdet.data import resolve_input_config
from timm.models.layers import set_layer_config
from flask import Flask, jsonify, request
import numpy as np

root_dir = Path.cwd().parent
output_dir = root_dir / "output" 

with open(str(Path.cwd() / "detection_config.yaml"),"r") as stream:
    try:
        data_yaml = yaml.load(stream, Loader=yaml.FullLoader)
        config = EasyDict(data_yaml["common"])
    except yaml.YAMLError as exc:
      print(exc)

config.model.model = "tf_efficientdet_d4"

id2name = {0:"Aortic enlargement",
    1: "Atelectasis",
    2:"Calcification",
    3 : "Cardiomegaly",
    4 : "Consolidation",
    5 : "ILD",
    6 : "Infiltration",
    7 : "Lung Opacity",
    8 : "Nodule/Mass",
    9 : "Other lesion",
    10 : "Pleural effusion",
    11 : "Pleural thickening",
    12 : "Pneumothorax",
    13 : "Pulmonary fibrosis",
    14: "No Findings"}


#Input to model should be [BATCH SIZE, CHANNELS, W,H]
root = os.getcwd()
model_name =  "tf_efficientdet_d4"
num_classes = 15
pretrained = False
checkpoint_path = str(output_dir / "0325_training_6_kaggle/checkpoint-16.pth.tar")#  from exp6
use_ema = False
redundant_bias = None
base_config = get_efficientdet_config(config.model.model)
base_config.image_size = (256,256) #override the [512,512]
with set_layer_config(scriptable=False):
  #base_config.norm_kwargs=dict(eps=.001, momentum=.01)

  bench = create_model_from_config(base_config, bench_task='predict', pretrained = pretrained,
                                  num_classes = num_classes, redundant_bias = None,
                                  checkpoint_path=checkpoint_path, 
                                  checkpoint_ema=use_ema)

model_config = bench.config
# model_config.image_size = (1024,1024) # is this the problem?it says 512,512n 
param_count = sum([m.numel() for m in bench.parameters()])
print('Model %s created, param count: %d' % (model_name, param_count))
bench  = bench.cuda()
amp_autocass = suppress
native_amp = True
amp_autocast = torch.cuda.amp.autocast
print("Using native Torch AMP. Validating in mixed precision.")
bench.eval()
score_threshold = 0.45 #0.35 the first time. #0.60 highest



def rescale_bboxes(bboxes, img_width, img_height):
    # Currently only supporting 256 x 256 images.
    # if different size than 256(default), I need to rescale as code below
    # otherwise it will stay the same(which is correct for now)

    def_img_size = 256
    x_scale = img_width/def_img_size
    y_scale = img_height/def_img_size
    
    if not np.array_equal(bboxes, np.array([[0,0,1,1]])):
        bboxes[:,[0,2]] = bboxes[:,[0,2]] * x_scale
        bboxes[:,[1,3]] = bboxes[:,[1,3]] * y_scale
    return bboxes

def transform_image(image_bytes):
    # my_transforms = transforms.Compose([transforms.Resize(255),
    #                                     transforms.CenterCrop(224),
    #                                     transforms.ToTensor(),
    #                                     transforms.Normalize(
    #                                         [0.485, 0.456, 0.406],
    #                                         [0.229, 0.224, 0.225])])
    my_transforms = transforms.Compose([transforms.ToTensor()])
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return my_transforms(image).unsqueeze(0)

def get_prediction(img_bytes):
    
    '''
    input: tensor of [B, C, W, H ] dimensions
    '''
    # convert form img read to tensor so that it can be used as input tho.
    with torch.no_grad():
        input = transform_image(img_bytes) #B,C,W,H
        img_width = input.shape[2]
        img_height = input.shape[3]
        input = input.cuda().float()
        with amp_autocast():
            batch_output = bench(input)
            batch_output = batch_output.cpu().numpy()
            for idx in range(batch_output.shape[0]):
                output = batch_output[idx,:,:]
                bboxes = output[:,:4]
                score = output[:,-2]
                label = output[:,-1]
                indices = np.where(score > score_threshold)
                label = label[indices]
                bboxes = bboxes[indices]
                score = score[indices]
                label = [id2name[infection] for infection in label]
                if indices[0].size == 0 or "No Findings" in label: #empty or "no finding"
                    bboxes = np.array([0,0,1,1], ndmin=2)
                    #emptyscore = np.array([1])
                    label = np.array([14]) #label[indices]
                    label = ["No Findings"]

                bboxes = rescale_bboxes(bboxes, img_width, img_height)
    return bboxes, score, label



app = Flask(__name__)
@app.route('/predict/', methods = ['POST'])
def predict():
    results = {}
    if request.method == 'POST':
        req = request.get_json(force=True) # why force = true?
        img_bytes = req["image"]
        img_bytes = base64.b64decode(img_bytes)
        bboxes, score, label = get_prediction(img_bytes)
        results = {"bbox": bboxes.tolist(), "score": score.tolist(), "label":label} #label.tolist()
        result_dict = {"results": results}
        print("[+] results {}".format(result_dict))
        return jsonify(result_dict)

@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', "*")
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

if __name__ == '__main__':
    app.run(debug = True,  host='0.0.0.0')

#use_reloader=False
