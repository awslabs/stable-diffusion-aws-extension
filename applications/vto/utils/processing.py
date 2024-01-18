import numpy as np
import pycocotools.mask as maskUtils
import math
import cv2
from PIL import Image, ImageDraw
import torch
from data.base_dataset import get_params, get_transform



demo_cloth_dir = './demo_samples/clothes'
demo_person_dir = './demo_samples/person'


resolution = 512

############### get palm mask ################
def get_mask_from_kps(kps, img_h, img_w):
    rles = maskUtils.frPyObjects(kps, img_h, img_w)
    rle = maskUtils.merge(rles)
    mask = maskUtils.decode(rle)[..., np.newaxis].astype(np.float32)
    mask = mask * 255.0
    return mask

def get_rectangle_mask(a, b, c, d, img_h, img_w):
    x1, y1 = a + (b-d)/4,   b + (c-a)/4
    x2, y2 = a - (b-d)/4,   b - (c-a)/4

    x3, y3 = c + (b-d)/4,   d + (c-a)/4
    x4, y4 = c - (b-d)/4,   d - (c-a)/4

    kps = [x1, y1, x2, y2]

    v0_x, v0_y = c-a,   d-b
    v1_x, v1_y = x3-x1, y3-y1
    v2_x, v2_y = x4-x1, y4-y1

    cos1 = (v0_x*v1_x+v0_y*v1_y) / \
        (math.sqrt(v0_x*v0_x+v0_y*v0_y)*math.sqrt(v1_x*v1_x+v1_y*v1_y))
    cos2 = (v0_x*v2_x+v0_y*v2_y) / \
        (math.sqrt(v0_x*v0_x+v0_y*v0_y)*math.sqrt(v2_x*v2_x+v2_y*v2_y))

    if cos1 < cos2:
        kps.extend([x3, y3, x4, y4])
    else:
        kps.extend([x4, y4, x3, y3])

    kps = np.array(kps).reshape(1, -1).tolist()
    mask = get_mask_from_kps(kps, img_h=img_h, img_w=img_w)

    return mask

def get_hand_mask(hand_keypoints, h, w):
    # shoulder, elbow, wrist
    s_x, s_y, s_c = hand_keypoints[0]
    e_x, e_y, e_c = hand_keypoints[1]
    w_x, w_y, w_c = hand_keypoints[2]

    up_mask = np.ones((h, w, 1), dtype=np.float32)
    bottom_mask = np.ones((h, w, 1), dtype=np.float32)
    if s_c > 0.1 and e_c > 0.1:
        up_mask = get_rectangle_mask(s_x, s_y, e_x, e_y, h, w)
        if resolution == 512:
            kernel = np.ones((50, 50), np.uint8)
        else:
            kernel = np.ones((100, 100), np.uint8)
        up_mask = cv2.dilate(up_mask, kernel, iterations=1)
        up_mask = (up_mask > 0).astype(np.float32)[..., np.newaxis]
    if e_c > 0.1 and w_c > 0.1:
        bottom_mask = get_rectangle_mask(e_x, e_y, w_x, w_y, h, w)
        if resolution == 512:
            kernel = np.ones((30, 30), np.uint8)
        else:
            kernel = np.ones((60, 60), np.uint8)
        bottom_mask = cv2.dilate(bottom_mask, kernel, iterations=1)
        bottom_mask = (bottom_mask > 0).astype(np.float32)[..., np.newaxis]

    return up_mask, bottom_mask

def get_palm_mask(hand_mask, hand_up_mask, hand_bottom_mask):
    inter_up_mask = ((hand_mask + hand_up_mask) == 2).astype(np.float32)
    hand_mask = hand_mask - inter_up_mask
    inter_bottom_mask = ((hand_mask+hand_bottom_mask)
                            == 2).astype(np.float32)
    palm_mask = hand_mask - inter_bottom_mask

    return palm_mask

def get_palm(parsing, keypoints):
    h, w = parsing.shape[0:2]

    left_hand_keypoints = keypoints[[5, 6, 7], :].copy()
    right_hand_keypoints = keypoints[[2, 3, 4], :].copy()

    left_hand_up_mask, left_hand_bottom_mask = get_hand_mask(
        left_hand_keypoints, h, w)
    right_hand_up_mask, right_hand_bottom_mask = get_hand_mask(
        right_hand_keypoints, h, w)

    # mask refined by parsing
    left_hand_mask = (parsing == 15).astype(np.float32)
    right_hand_mask = (parsing == 16).astype(np.float32)

    left_palm_mask = get_palm_mask(
        left_hand_mask, left_hand_up_mask, left_hand_bottom_mask)
    right_palm_mask = get_palm_mask(
        right_hand_mask, right_hand_up_mask, right_hand_bottom_mask)
    palm_mask = ((left_palm_mask + right_palm_mask) > 0).astype(np.uint8)

    return palm_mask

def get_person_info(opt, person_image, pose_data, dense_mask, parsing):
    # person image
    P = person_image
    print(P.size)
    params = get_params(opt, P.size)
    print(params)
    transform_for_rgb = get_transform(opt, params)
    P_tensor = transform_for_rgb(P)

    # person 2d pose
    fine_height=512
    fine_width=384
    radius=8
        
    point_num = pose_data.shape[0]
    pose_map = torch.zeros(point_num, fine_height, fine_width)
    r = radius
    im_pose = Image.new('L', (fine_width, fine_height))
    pose_draw = ImageDraw.Draw(im_pose)
    for i in range(point_num):
        one_map = Image.new('L', (fine_width, fine_height))
        draw = ImageDraw.Draw(one_map)
        pointx = pose_data[i, 0]
        pointy = pose_data[i, 1]
        if pointx > 1 and pointy > 1:
            draw.rectangle((pointx-r, pointy-r, pointx+r, pointy+r), 'white', 'white')
            pose_draw.rectangle((pointx-r, pointy-r, pointx+r, pointy+r), 'white', 'white')
        one_map = transform_for_rgb(one_map.convert('RGB'))
        pose_map[i] = one_map[0]
    Pose_tensor = pose_map

    # person 3d pose
    transform_for_mask = get_transform(opt, params, method=Image.NEAREST, normalize=False)
    dense_mask_tensor = transform_for_mask(dense_mask) * 255.0
    dense_mask_tensor = dense_mask_tensor[0:1, ...]

    # person parsing
    parsing_tensor = transform_for_mask(parsing) * 255.0
    
    parsing_np = (parsing_tensor.numpy().transpose(1, 2, 0)[..., 0:1]).astype(np.uint8)
    palm_mask_np = get_palm(parsing_np, pose_data)

    if np.max(parsing_np) > 20:
        person_clothes_left_sleeve_mask_np = (parsing_np==21).astype(int) + \
                                        (parsing_np==24).astype(int)
        person_clothes_torso_mask_np = (parsing_np==5).astype(int) + \
                                    (parsing_np==6).astype(int) + \
                                    (parsing_np==7).astype(int)
        person_clothes_right_sleeve_mask_np = (parsing_np==22).astype(int) + \
                                            (parsing_np==25).astype(int)
        person_clothes_mask_np = person_clothes_left_sleeve_mask_np + \
                                person_clothes_torso_mask_np + \
                                person_clothes_right_sleeve_mask_np
    else:
        person_clothes_mask_np = (parsing_np==5).astype(int) + \
                                    (parsing_np==6).astype(int) + \
                                    (parsing_np==7).astype(int)
    
    #print(person_clothes_mask_np.shape)
    #Image.fromarray(person_clothes_mask_np[:,:,0].astype(np.uint8) * 255).save('temp_show/person_clothes_mask_np1111.png')
    
    #left_arm_mask_np = (parsing_np==15).astype(int)
    #right_arm_mask_np = (parsing_np==16).astype(int)
    hand_mask_np = (parsing_np==15).astype(int) + (parsing_np==16).astype(int)
    neck_mask_np = (parsing_np==11).astype(int)

    
    person_clothes_mask_tensor = torch.tensor(person_clothes_mask_np.transpose(2, 0, 1)).float()


    ### preserve region mask 
    if np.max(parsing_np) > 20:       
        preserve_mask_for_loss_np = np.array([(parsing_np==index).astype(int) for index in [1,2,3,4,8,9,10,12,13,14,17,18,19,20]])
        preserve_mask_for_loss_np = np.sum(preserve_mask_for_loss_np,axis=0)
        

        preserve_mask_np = np.array([(parsing_np==index).astype(int) for index in [1,2,3,4,8,9,10,12,13,14,17,18,19,20]])
        preserve_mask_np = np.sum(preserve_mask_np,axis=0)
    else:
        preserve_mask_for_loss_np = np.array([(parsing_np==index).astype(int) for index in [1,2,3,4,8,9,10,12,13,14,17,18,19,20]])
        preserve_mask_for_loss_np = np.sum(preserve_mask_for_loss_np,axis=0)
        
        preserve_mask_np = np.array([(parsing_np==index).astype(int) for index in [1,2,3,4,8,9,10,12,13,14,17,18,19,20]])
        preserve_mask_np = np.sum(preserve_mask_np,axis=0)   

    preserve_mask1_np = preserve_mask_for_loss_np + palm_mask_np
    preserve_mask2_np = preserve_mask_for_loss_np + hand_mask_np
    preserve_mask3_np = preserve_mask_np + palm_mask_np

    preserve_mask1_tensor = torch.tensor(preserve_mask1_np.transpose(2,0,1)).float()
    preserve_mask2_tensor = torch.tensor(preserve_mask2_np.transpose(2,0,1)).float()
    preserve_mask3_tensor = torch.tensor(preserve_mask3_np.transpose(2,0,1)).float()

    # Image.fromarray(palm_mask_np[:,:,0].astype(np.uint8) * 255).save('temp_show/palm_mask_np1111.png')
    # Image.fromarray(hand_mask_np[:,:,0].astype(np.uint8) * 255).save('temp_show/hand_mask_np1111.png')

    # Image.fromarray(preserve_mask1_np[:,:,0].astype(np.uint8) * 255).save('temp_show/preserve_mask1_np1111.png')
    # Image.fromarray(preserve_mask2_np[:,:,0].astype(np.uint8) * 255).save('temp_show/preserve_mask2_np1111.png')
    # Image.fromarray(preserve_mask3_np[:,:,0].astype(np.uint8) * 255).save('temp_show/preserve_mask3_np1111.png')

    ### skin color
    face_mask_np = (parsing_np==14).astype(np.uint8)
    skin_mask_np = (face_mask_np+hand_mask_np+neck_mask_np).astype(np.uint8)
    P_np = np.array(P)
    skin = skin_mask_np * P_np
    skin_r = skin[..., 0].reshape((-1))
    skin_g = skin[..., 1].reshape((-1))
    skin_b = skin[..., 2].reshape((-1))
    skin_r_valid_index = np.where(skin_r > 0)[0]
    skin_g_valid_index = np.where(skin_g > 0)[0]
    skin_b_valid_index = np.where(skin_b > 0)[0]

    skin_r_median = np.median(skin_r[skin_r_valid_index])
    skin_g_median = np.median( skin_g[skin_g_valid_index])
    skin_b_median = np.median(skin_b[skin_b_valid_index])

    arms_r = np.ones_like(parsing_np[...,0:1]) * skin_r_median
    arms_g = np.ones_like(parsing_np[...,0:1]) * skin_g_median
    arms_b = np.ones_like(parsing_np[...,0:1]) * skin_b_median
    arms_color = np.concatenate([arms_r,arms_g,arms_b],2).transpose(2,0,1)
    AMC_tensor = torch.FloatTensor(arms_color)
    AMC_tensor = AMC_tensor / 127.5 - 1.0

    person_input_dict = {
        'image': P_tensor.unsqueeze(0), 'pose':Pose_tensor.unsqueeze(0) , 'densepose':dense_mask_tensor.unsqueeze(0),
        'person_clothes_mask': person_clothes_mask_tensor.unsqueeze(0),
        'preserve_mask': preserve_mask1_tensor.unsqueeze(0), 'preserve_mask2': preserve_mask2_tensor.unsqueeze(0),
        'preserve_mask3': preserve_mask3_tensor.unsqueeze(0),
        'arms_color': AMC_tensor.unsqueeze(0)
        }

    return person_input_dict

def get_cloth_info(cloth_image, cloth_mask, cloth_parsing, opt):
    ### clothes
    C = cloth_image
    params = get_params(opt, C.size)
    transform_for_rgb = get_transform(opt, params)
    C_tensor = transform_for_rgb(C)
    
    CM = cloth_mask
    transform_for_mask = get_transform(opt, params, method=Image.NEAREST, normalize=False)
    CM_tensor = transform_for_mask(CM)

    cloth_parsing_tensor = transform_for_mask(cloth_parsing) * 255.0
    cloth_parsing_tensor = cloth_parsing_tensor[0:1, ...]

    cloth_parsing_np = (cloth_parsing_tensor.numpy().transpose(1,2,0)).astype(int)
    flat_cloth_left_mask_np = (cloth_parsing_np==21).astype(int)
    flat_cloth_middle_mask_np = (cloth_parsing_np==5).astype(int) + \
                                (cloth_parsing_np==24).astype(int) + \
                                (cloth_parsing_np==13).astype(int)
    flat_cloth_right_mask_np = (cloth_parsing_np==22).astype(int)
    flat_cloth_label_np = flat_cloth_left_mask_np * 1 + flat_cloth_middle_mask_np * 2 + flat_cloth_right_mask_np * 3
    flat_cloth_label_np = flat_cloth_label_np / 3

    flat_cloth_left_mask_tensor = torch.tensor(flat_cloth_left_mask_np.transpose(2, 0, 1)).float()
    flat_cloth_middle_mask_tensor = torch.tensor(flat_cloth_middle_mask_np.transpose(2, 0, 1)).float()
    flat_cloth_right_mask_tensor = torch.tensor(flat_cloth_right_mask_np.transpose(2, 0, 1)).float()

    flat_cloth_label_tensor = torch.tensor(flat_cloth_label_np.transpose(2, 0, 1)).float()
    
    C_type = 'upper'

    cloth_input_dict = {
        'color': C_tensor.unsqueeze(0), 'edge': CM_tensor.unsqueeze(0), 
        'flat_clothes_left_mask': flat_cloth_left_mask_tensor.unsqueeze(0),
        'flat_clothes_middle_mask': flat_cloth_middle_mask_tensor.unsqueeze(0),
        'flat_clothes_right_mask': flat_cloth_right_mask_tensor.unsqueeze(0),
        'flat_clothes_label': flat_cloth_label_tensor.unsqueeze(0),
        'c_type': C_type, 
    }

    return cloth_input_dict
