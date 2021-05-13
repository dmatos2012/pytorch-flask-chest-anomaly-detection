from PIL import Image
import io
import torchvision.transforms as transforms
import matplotlib.pyplot as plt

import requests
resp = requests.post("http://localhost:5000/predict",
                     files={"file": open('./vinbigdata/test/0a6fd1c1d71ff6f9e0f0afa746e223e4.png','rb')})
print(resp.json())


#0a1addecfc432a1b425d61fe57bc29d2.png


# def transform_image(image_bytes):
#     # my_transforms = transforms.Compose([transforms.Resize(255),
#     #                                     transforms.CenterCrop(224),
#     #                                     transforms.ToTensor(),
#     #                                     transforms.Normalize(
#     #                                         [0.485, 0.456, 0.406],
#     #                                         [0.229, 0.224, 0.225])])
#     my_transforms = transforms.Compose([transforms.ToTensor()])
#     image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
#     return my_transforms(image).unsqueeze(0)


# with open('./sample_imgs/0a0ac65c40a9ac441651e4bfbde03c4e.png','rb') as f:
#     img_bytes = f.read()
#     tensor = transform_image(img_bytes)
#     print(tensor.shape)
#     tensor = torch.squeeze(tensor)
#     tensor = tensor.permute(1,2,0)
#     plt.imshow(tensor)
#     plt.show()
 


# 0a0ac65c40a9ac441651e4bfbde03c4e.png