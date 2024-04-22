import glob
import os
import cv2
import argparse
import math
from PIL import Image
import numpy as np
from utils import split_s3_path, upload_file_to_s3, download_file_from_s3

def resize_image(src_img_s3_path, max_resolution="512x512", divisible_by=2, interpolation=None):
  #split s3 path
  bucket_name, key_src = split_s3_path(src_img_s3_path)
  key_dst = os.path.dirname(key_src) + '_crop/' + os.path.basename(key_src)
  #dowload file for src_img_s3_path
  local_src_folder = os.path.join('/tmp', os.path.dirname(key_src))
  local_dst_folder = os.path.join('/tmp', os.path.dirname(key_src) + '_crop')
  os.makedirs(local_src_folder, exist_ok=True)
  os.makedirs(local_dst_folder, exist_ok=True)

  local_src_file_path = os.path.join(local_src_folder, os.path.basename(key_src))
  local_dst_file_path = os.path.join(local_dst_folder, os.path.basename(key_src))

  download_file_from_s3(bucket_name, key_src, local_src_file_path)

  # Select interpolation method
  if interpolation == 'lanczos4':
    cv2_interpolation = cv2.INTER_LANCZOS4
  elif interpolation == 'cubic':
    cv2_interpolation = cv2.INTER_CUBIC
  else:
    cv2_interpolation = cv2.INTER_AREA

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
    img = np.array(image, np.uint8)
    
    # Calculate max_pixels from max_resolution string
    max_pixels = int(max_resolution.split("x")[0]) * int(max_resolution.split("x")[1])

    # Calculate current number of pixels
    current_pixels = img.shape[0] * img.shape[1]

    # Check if the image needs resizing
    if current_pixels > max_pixels:
      # Calculate scaling factor
      scale_factor = max_pixels / current_pixels

      # Calculate new dimensions
      new_height = int(img.shape[0] * math.sqrt(scale_factor))
      new_width = int(img.shape[1] * math.sqrt(scale_factor))

      # Resize image
      img = cv2.resize(img, (new_width, new_height), interpolation=cv2_interpolation)
    else:
      new_height, new_width = img.shape[0:2]

    # Calculate the new height and width that are divisible by divisible_by (with/without resizing)
    new_height = new_height if new_height % divisible_by == 0 else new_height - new_height % divisible_by
    new_width = new_width if new_width % divisible_by == 0 else new_width - new_width % divisible_by

    # Center crop the image to the calculated dimensions
    y = int((img.shape[0] - new_height) / 2)
    x = int((img.shape[1] - new_width) / 2)
    img = img[y:y + new_height, x:x + new_width]

    # Save resized image in dst_img_folder
    image = Image.fromarray(img)
    image.save(local_dst_file_path, quality=100)

    #proc = "Resized" if current_pixels > max_pixels else "Saved"
    #print(f"{proc} image: {os.path.basename(key_src)} with size {img.shape[0]}x{img.shape[1]}")
    upload_file_to_s3(local_dst_file_path, bucket_name, key_dst)


def setup_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description='Resize image on s3 to a specified max resolution(s) / 指定されたフォルダ内の画像を指定した最大画像サイズ（面積）以下にアスペクト比を維持したままリサイズします')
  parser.add_argument('src_img_s3_path', type=str, help='Source folder containing the images / 元画像のフォルダ')
  parser.add_argument('--max_resolution', type=str,
                      help='Maximum resolution(s) in the format "512x512,384x384, etc, etc" / 最大画像サイズをカンマ区切りで指定 ("512x512,384x384, etc, etc" など)', default="512x512,384x384,256x256,128x128")
  parser.add_argument('--divisible_by', type=int,
                      help='Ensure new dimensions are divisible by this value / リサイズ後の画像のサイズをこの値で割り切れるようにします', default=1)
  parser.add_argument('--interpolation', type=str, choices=['area', 'cubic', 'lanczos4'],
                      default='area', help='Interpolation method for resizing / リサイズ時の補完方法')
  
  return parser


def main():
  parser = setup_parser()

  args = parser.parse_args()
  resize_image(args.src_img_s3_path, args.dst_img_s3_path, args.max_resolution,
                args.divisible_by, args.interpolation)


if __name__ == '__main__':
  main()
