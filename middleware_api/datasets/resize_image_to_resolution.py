import glob
import os
import argparse
import math
from PIL import Image
import numpy as np
from utils import split_s3_path, upload_file_to_s3, download_file_from_s3

def resize_image(src_img_s3_path, max_resolution="512x512", interpolation='lanczos'):
  #split s3 path
  bucket_name, key_src = split_s3_path(src_img_s3_path)
  key_dst = os.path.dirname(key_src) + '_' + max_resolution + os.path.basename(key_src)
  #dowload file for src_img_s3_path
  local_src_folder = os.path.join('/tmp', os.path.dirname(key_src))
  local_dst_folder = os.path.join('/tmp', os.path.dirname(key_src) + '_crop')
  os.makedirs(local_src_folder, exist_ok=True)
  os.makedirs(local_dst_folder, exist_ok=True)

  local_src_file_path = os.path.join(local_src_folder, os.path.basename(key_src))
  local_dst_file_path = os.path.join(local_dst_folder, os.path.basename(key_src))

  download_file_from_s3(bucket_name, key_src, local_src_file_path)

  # Select interpolation method
  if interpolation == 'lanczos':
    interpolation_type = Image.LANCZOS
  elif interpolation == 'cubic':
    interpolation_type = Image.BICUBIC
  else:
    interpolation_type = Image.NEAREST

  # Iterate through all files in src_img_folder
  img_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")                   # copy from train_util.py
  
  # Check if the image is png, jpg or webp etc...
  if not local_src_file_path.endswith(img_exts):
    # upload the file to the destination s3 path (.txt or .caption or etc.)
    upload_file_to_s3(local_src_file_path, bucket_name, key_dst)
  else:
    # Load image
    image = Image.open(local_src_file_path)
    if not image.mode == "RGB":
      image = image.convert("RGB")
    
    # Calculate max_pixels from max_resolution string
    width = int(max_resolution.split("x")[0])
    height = int(max_resolution.split("x")[1])

    # Calculate current number of pixels
    current_height = image.size[1]
    current_width = image.size[0]

    # Check if the image needs resizing
    if current_width > width and current_height > height:
      # Calculate scaling factor
      scale_factor_width = width / current_width
      scale_factor_height = height / current_height

      if scale_factor_height > scale_factor_width:
        new_width = math.ceil(current_width * scale_factor_height)
        image = image.resize((new_width, height), interpolation_type)
      elif scale_factor_height < scale_factor_width:
        new_height = math.ceil(current_height * scale_factor_width)
        image = image.resize((width, new_height), interpolation_type)
      else:
        image = image.resize((width, height), interpolation_type)
    
    resized_img = np.array(image)
    new_img = np.zeros((height, width, 3), dtype=np.uint8)

    # Center crop the image to the calculated dimensions
    new_y = 0
    new_x = 0
    height_dst = height
    width_dst = width
    y = int((resized_img.shape[0] - height) / 2)
    if y < 0:
      new_y = -y
      height_dst = resized_img.shape[0]
      y = 0
    x = int((resized_img.shape[1] - width) / 2)
    if x < 0:
      new_x = -x
      width_dst = resized_img.shape[1]
      x = 0
    new_img[new_y:new_y+height_dst, new_x:new_x+width_dst] = resized_img[y:y + height_dst, x:x + width_dst]

    # Save resized image in dst_img_folder
    image = Image.fromarray(new_img)
    image.save(local_dst_file_path, quality=100)

    upload_file_to_s3(local_dst_file_path, bucket_name, key_dst)


def setup_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description='Resize image on s3 to a specified max resolution(s) / 指定されたフォルダ内の画像を指定した最大画像サイズ（面積）以下にアスペクト比を維持したままリサイズします')
  parser.add_argument('src_img_s3_path', type=str, help='Source folder containing the images / 元画像のフォルダ')
  parser.add_argument('--max_resolution', type=str,
                      help='Maximum resolution(s) in the format "512x512,384x384, etc, etc" / 最大画像サイズをカンマ区切りで指定 ("512x512,384x384, etc, etc" など)', default="512x512,384x384,256x256,128x128")
  parser.add_argument('--interpolation', type=str, choices=['area', 'cubic', 'lanczos4'],
                      default='area', help='Interpolation method for resizing / リサイズ時の補完方法')
  
  return parser


def main():
  parser = setup_parser()

  args = parser.parse_args()
  resize_image(args.src_img_s3_path, args.max_resolution, args.interpolation)


if __name__ == '__main__':
  main()
