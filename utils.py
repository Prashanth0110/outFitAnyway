import os
import sys
import cv2
import json
import random
import time
import requests
import func_timeout
import numpy as np
import streamlit as st
from urllib.parse import urlparse


# Configuration - Update these based on your storage solution
# Option 1: Local storage (development)
USE_LOCAL_STORAGE = True
LOCAL_STORAGE_PATH = "static_files"

# Option 2: AWS S3 (recommended for production)
USE_S3 = False
S3_BUCKET_NAME = "your-bucket-name"
S3_REGION = "us-east-1"

# Option 3: Cloudflare R2 (free tier available)
USE_R2 = False
R2_ACCOUNT_ID = "your-account-id"
R2_BUCKET_NAME = "your-bucket-name"

# API Configuration
TOKEN = os.environ.get('TOKEN', '')
UKAPIURL = os.environ.get('UKAPIURL', '')
POSEToken = os.environ.get('POSEToken', '')
Regions = "IndiaPakistanBengal"

# Project paths
proj_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(proj_dir, 'Datas')
tmpFolder = "tmp"
os.makedirs(tmpFolder, exist_ok=True)
os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)


def get_tips():
    """Get tip images - using local storage"""
    if USE_LOCAL_STORAGE:
        tip1 = os.path.join(LOCAL_STORAGE_PATH, 'tip1.jpg')
        tip2 = os.path.join(LOCAL_STORAGE_PATH, 'tip2.jpg')
        # If files don't exist locally, you can provide default paths
        if not os.path.exists(tip1):
            tip1 = "https://via.placeholder.com/400x300?text=Tip+1"
        if not os.path.exists(tip2):
            tip2 = "https://via.placeholder.com/400x300?text=Tip+2"
    else:
        # Use your storage service URL
        tip1 = f"https://your-storage-url.com/tips/tip1.jpg"
        tip2 = f"https://your-storage-url.com/tips/tip2.jpg"
    
    return tip1, tip2


def get_cloth_examples(hr=0):
    """Get clothing examples from local directory"""
    cloth_dir = os.path.join(data_dir, 'ClothImgs')
    examples = []
    
    if not os.path.exists(cloth_dir):
        return examples
    
    files = sorted(os.listdir(cloth_dir))
    hr_clothes = list(range(588, 597))
    
    for f in files:
        if '.jpg' not in f and '.png' not in f:
            continue
        
        cloth_id = f.split(".")[0]
        if int(cloth_id) in hr_clothes and hr == 0:
            continue
        if int(cloth_id) not in hr_clothes and hr == 1:
            continue
        
        cloth_path = os.path.join(cloth_dir, f)
        examples.append(cloth_path)
    
    examples = examples[::-1]
    return examples


def get_pose_examples():
    """Get pose examples from local directory"""
    pose_dir = os.path.join(data_dir, 'PoseImgs')
    examples = []
    
    if not os.path.exists(pose_dir):
        return examples
    
    for f in os.listdir(pose_dir):
        if '.jpg' not in f and '.png' not in f:
            continue
        pose_path = os.path.join(pose_dir, f)
        examples.append(pose_path)
    
    return examples


def get_client_ip():
    """Get client IP address in Streamlit"""
    try:
        # Try to get from Streamlit context
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers and 'X-Forwarded-For' in headers:
            return headers['X-Forwarded-For'].split(',')[0].strip()
    except:
        pass
    return "127.0.0.1"


def is_http_resource_accessible(url):
    """Check if HTTP resource is accessible"""
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking resource accessibility: {e}")
        return False


def upload_to_s3(file_path, file_name):
    """Upload file to AWS S3 - FREE TIER: 5GB storage, 20,000 GET requests, 2,000 PUT requests/month"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        
        s3_client.upload_file(file_path, S3_BUCKET_NAME, file_name)
        url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{file_name}"
        return url
    except Exception as e:
        print(f"S3 upload error: {e}")
        return ""


def upload_to_r2(file_path, file_name):
    """Upload file to Cloudflare R2 - FREE TIER: 10GB storage, unlimited egress"""
    try:
        import boto3
        
        s3_client = boto3.client(
            's3',
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ.get('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('R2_SECRET_ACCESS_KEY'),
            region_name='auto'
        )
        
        s3_client.upload_file(file_path, R2_BUCKET_NAME, file_name)
        # You need to configure a public domain for R2
        url = f"https://your-r2-domain.com/{file_name}"
        return url
    except Exception as e:
        print(f"R2 upload error: {e}")
        return ""


def upload_to_imgur(file_path):
    """Upload to Imgur - FREE: Unlimited uploads with rate limits"""
    try:
        client_id = os.environ.get('IMGUR_CLIENT_ID')
        if not client_id:
            return ""
        
        headers = {'Authorization': f'Client-ID {client_id}'}
        with open(file_path, 'rb') as f:
            response = requests.post(
                'https://api.imgur.com/3/image',
                headers=headers,
                files={'image': f}
            )
        
        if response.status_code == 200:
            return response.json()['data']['link']
        return ""
    except Exception as e:
        print(f"Imgur upload error: {e}")
        return ""


def upload_pose_img(clientIp, timeId, img):
    """Upload pose image to storage service"""
    fileName = clientIp.replace(".", "") + str(timeId) + ".jpg"
    local_path = os.path.join(tmpFolder, fileName)
    
    # Read and save image locally first
    img_data = cv2.imread(img)
    cv2.imwrite(local_path, img_data)
    
    # Choose upload method based on configuration
    upload_url = ""
    
    if USE_LOCAL_STORAGE:
        # For local development, use Streamlit's file serving
        # Copy to static folder
        static_path = os.path.join(LOCAL_STORAGE_PATH, fileName)
        cv2.imwrite(static_path, img_data)
        upload_url = static_path  # Return local path
    
    elif USE_S3:
        upload_url = upload_to_s3(local_path, fileName)
    
    elif USE_R2:
        upload_url = upload_to_r2(local_path, fileName)
    
    else:
        # Use original API upload (if available)
        json_data = {
            "token": "c0e69e5d129b11efa10c525400b75156",
            "input1": fileName,
            "input2": "",
            "protocol": "",
            "cloud": "ali"
        }
        
        session = requests.session()
        try:
            ret = requests.post(
                f"{UKAPIURL}/upload",
                headers={'Content-Type': 'application/json'},
                json=json_data,
                timeout=30
            )
            
            if ret.status_code == 200:
                if 'upload1' in ret.json():
                    upload_url_endpoint = ret.json()['upload1']
                    headers = {'Content-Type': 'image/jpeg'}
                    response = session.put(
                        upload_url_endpoint,
                        data=open(local_path, 'rb').read(),
                        headers=headers
                    )
                    if response.status_code == 200:
                        upload_url = upload_url_endpoint
        except Exception as e:
            print(f"Upload error: {e}")
    
    # Clean up temporary file
    if os.path.exists(local_path) and not USE_LOCAL_STORAGE:
        os.remove(local_path)
    
    return upload_url


def publicClothSwap(image, clothId, is_hr=0):
    """Submit cloth swap task to API"""
    json_data = {
        "image": image,
        "task_type": "11",
        "param1": str(clothId),
        "param2": "",
        "param3": "",
        "param4": str(is_hr),
        "delete_if_complete": "1",
        "force_celery": "0"
    }
    
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        ret = requests.post(
            f'{UKAPIURL}/public_advton',
            headers=headers,
            json=json_data,
            timeout=30
        )
        
        if ret.status_code == 200:
            response = ret.json()
            if 'mid_result' in response and 'id' in response:
                return {
                    'mid_result': response['mid_result'],
                    'id': response['id'],
                    "msg": response.get('msg', '')
                }
        return None
    except Exception as e:
        print(f"publicClothSwap error: {e}")
        return None


def getInfRes(taskId):
    """Get inference result status"""
    headers = {'Content-Type': 'application/json'}
    json_data = {'id': taskId}
    
    try:
        ret = requests.post(
            f'{UKAPIURL}/status_advton',
            headers=headers,
            json=json_data,
            timeout=10
        )
        
        if ret.status_code == 200:
            response = ret.json()
            if 'status' in response:
                return response
        return None
    except Exception as e:
        print(f"getInfRes error: {e}")
        return None


@func_timeout.func_set_timeout(10)
def check_region(ip):
    """Check if IP is from restricted region"""
    try:
        ret = requests.get(f"https://realip.cc/?ip={ip}", timeout=5)
        nat = ret.json()['country'].lower()
        if nat in Regions.lower():
            print(nat, 'invalid', ip)
            return False
        else:
            print(nat, 'valid', ip)
        return True
    except Exception as e:
        print(f"Region check error: {e}")
        return True


def check_region_warp(ip):
    """Wrapper for region check with error handling"""
    try:
        return check_region(ip)
    except Exception as e:
        print(e)
        return True


def public_pose_changer(image_url, prompt="Change the pose: two hands on hips.#Change the pose: arms extended."):
    """Submit pose change request to API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }
    
    json_data = {
        'image': image_url,
        'param1': 'pose_change',
        'param2': prompt,
        'param3': '',
        'param4': '',
        'param5': '',
        'is_private': '0',
        'delete_if_complete': '0'
    }
    
    try:
        ret = requests.post(
            f'{UKAPIURL}/public_comfyui',
            headers=headers,
            json=json_data,
            timeout=30
        )
        
        if ret.status_code == 200:
            response = ret.json()
            if 'id' in response:
                return {'id': response['id'], 'msg': response.get('msg', '')}
        return None
    except Exception as e:
        print(f"Pose changer error: {e}")
        return None


def get_pose_changer_res(task_id):
    """Get pose changer result status"""
    headers = {'Content-Type': 'application/json'}
    
    try:
        ret = requests.post(
            f'{UKAPIURL}/status_comfyui',
            headers=headers,
            json={'id': task_id},
            timeout=10
        )
        
        if ret.status_code == 200:
            return ret.json()
        return None
    except Exception as e:
        print(f"Get pose changer result error: {e}")
        return None


def download_result_image(image_url, filename=None):
    """Download result image from URL and save locally"""
    try:
        if filename is None:
            filename = f"result_{int(time.time())}.jpg"
        
        local_path = os.path.join(tmpFolder, filename)
        
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            return local_path
        return None
    except Exception as e:
        print(f"Download result image error: {e}")
        return None