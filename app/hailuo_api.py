import requests
import cloudscraper
import hashlib
import uuid
import time
from requests.exceptions import RequestException
from urllib.parse import quote
import json
import oss2
from oss2 import StsAuth, Bucket
from uuid import uuid4
import os


# 设备信息有效期
DEVICE_INFO_EXPIRES = 10800
# 伪装headers
FAKE_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Origin": "https://hailuoai.video",
    "Pragma": "no-cache",
    "Priority": "u=1, i",
    "Sec-Ch-Ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}

# 伪装数据
FAKE_USER_DATA = {
    "device_platform": "web",
    "app_id": "3001",
    "version_code": "22202",
    "biz_id": 0,
    "uuid": None,
    "device_id": None,
    "lang": "en",
    "os_name": "Mac",
    "browser_name": "chrome",
    "device_memory": 8,
    "cpu_core_num": 8,
    "browser_language": "en-US",
    "browser_platform": "MacIntel",
    "screen_width": 1440,
    "screen_height": 900,
    "unix": None,
}

# 文件最大大小
FILE_MAX_SIZE = 100 * 1024 * 1024
# 设备信息映射
device_info_map = {}
# 设备信息请求队列映射
device_info_request_queue_map = {}

# 创建全局的cloudscraper实例，避免每次请求都创建新实例导致内存泄漏
_global_scraper = None

def get_scraper():
    """获取全局的cloudscraper实例"""
    global _global_scraper
    if _global_scraper is None:
        _global_scraper = cloudscraper.create_scraper()
    return _global_scraper

def reset_scraper():
    """重置全局的cloudscraper实例"""
    global _global_scraper
    if _global_scraper:
        try:
            _global_scraper.close()
        except:
            pass
    _global_scraper = None

def request_device_info(token):
    if token in device_info_request_queue_map:
        print(f"Token: {token} in device_info_request_queue_map",device_info_request_queue_map[token])
        if device_info_request_queue_map[token] and int(time.time()) < device_info_request_queue_map[token]["refreshTime"]:
            return device_info_request_queue_map[token]
    
    device_info_request_queue_map[token] = {}
    
    try:
        user_id = str(uuid.uuid4())
        result = request("POST", "/v1/api/user/device/register", {"uuid": user_id}, token, {"userId": user_id}, {"params": FAKE_USER_DATA})
        print(result,"result")
        device_id_str = check_result(result)
        device_info = {
            "deviceId": device_id_str,
            "userId": user_id,
            "refreshTime": int(time.time()) + DEVICE_INFO_EXPIRES,
        }
        device_info_request_queue_map[token] = device_info
        
        return device_info
    except Exception as err:
        print(err)
        raise err

def acquire_device_info(token):
    result = device_info_map.get(token)
    if not result:
        result = request_device_info(token)
        device_info_map[token] = result
    if int(time.time()) > result["refreshTime"]:
        result = request_device_info(token)
        device_info_map[token] = result
    return result

# def check_file_url(file_url):
#     if is_base64_data(file_url):
#         return
#     try:
#         response = requests.head(file_url, timeout=15)
#         if response.status_code >= 400:
#             raise Exception(f"File {file_url} is not valid: [{response.status_code}] {response.reason}")
#         if "content-length" in response.headers:
#             file_size = int(response.headers["content-length"])
#             if file_size > FILE_MAX_SIZE:
#                 raise Exception(f"File {file_url} exceeds size limit")
#     except RequestException as e:
#         raise Exception(f"Error checking file URL: {e}")

# def upload_file(file_url, token):
#     check_file_url(file_url)
#     # Implement file upload logic here
#     pass

def check_result(result):
    if not result:
        return None
    status_info = result.get("statusInfo")
    if not isinstance(status_info, dict):
        return result
    code = status_info.get("code")
    message = status_info.get("message")
    if code == 0:
        return result.get("data").get("deviceIDStr")
    raise Exception(f"[请求hailuo失败]: {message}")

def request(method, uri, data, token, device_info, options=None):
    if options is None:
        options = {}
    else:
      FAKE_USER_DATA.update(options.get("params", {}))
    unix = str(int(time.time())*1000)
    # unix = "1729176517000"
    
    # print(FAKE_USER_DATA,'FAKE_USER_DATA')
    user_data = FAKE_USER_DATA.copy()
    user_data["uuid"] = device_info["userId"]
    user_data["device_id"] = device_info.get("deviceId")
    user_data["unix"] = unix
    query_str = "&".join(f"{key}={value}" for key, value in user_data.items() if value is not None)
    # print(f"query_str: {query_str}")
    data_json = json.dumps(data)
    # print(f"data_json: {data_json}")
    full_uri = f"{uri}?{query_str}"
    # full_uri = quote(full_uri)
    u = quote(full_uri, safe='')
    
    # print(f"full_uri: {u}")
    u = f"{u}_{data_json}{hashlib.md5(unix.encode()).hexdigest()}ooui".encode()
    
    # print(f"u: {u}")
    
    yy = hashlib.md5(u).hexdigest()
    # print(f"yy: {yy}")
    trace_id = str(uuid.uuid4())
    # print(f"trace_id: {trace_id}")
    headers = {
        "Referer": "https://hailuoai.video/",
        "Accept-Encoding": "identity",
        "Accept": "application/json, text/plain, */*",
        "Token": token,
        **FAKE_HEADERS,
        # "Baggage": f"sentry-environment=production,sentry-release=QlRIxmZEEG1FnXWGSW1R7,sentry-public_key=6cf106db5c7b7262eae7cc6b411c776a,sentry-trace_id={trace_id},sentry-sample_rate=1,sentry-sampled=true",
        # "Sentry-Trace": f"{trace_id}-{str(uuid.uuid4())[:16]}-1",
        "Yy": yy,
    }
    headers.update(options.get("headers", {}))
    try:
        # 使用全局的scraper实例，避免每次创建新实例
        scraper = get_scraper()
        response = scraper.request(method, f"https://hailuoai.video{full_uri}", json=data, headers=headers, timeout=15)
        response_text = response.text
        # print("================")
        # print("data",data)
        # print("response.status_code",response.status_code)
        # print("response.text",response.text)
        # print("================")
        return json.loads(response_text)
    except RequestException as e:
        # 如果请求失败，尝试重置scraper并重试一次
        try:
            print(f"Request failed, resetting scraper and retrying: {e}")
            reset_scraper()
            scraper = get_scraper()
            response = scraper.request(method, f"https://hailuoai.video{full_uri}", json=data, headers=headers, timeout=15)
            response_text = response.text
            return json.loads(response_text)
        except RequestException as retry_e:
            raise Exception(f"Request failed after retry: {retry_e}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")

# 其他函数可以根据需要进行转换
def upload_to_oss(access_key_id, access_key_secret, security_token, local_file_path, endpoint, bucket_name,dir,token,device_info):
    
    # 获取文件扩展名
    extension = local_file_path.split('.').pop()
    # print(extension)
    # 生成唯一的对象名称
    fileName = f"{uuid4()}.{extension}"
    object_name = f"{dir}/{fileName}"
    # print(object_name)
    # 创建STS授权
    auth = StsAuth(access_key_id, access_key_secret, security_token)
    # 创建Bucket对象
    bucket = Bucket(auth, endpoint, bucket_name)
    # print(bucket)
    url = f"http://{bucket_name}.{endpoint}/{object_name}"
    try:
        # 上传文件
        result = bucket.put_object_from_file(object_name, local_file_path)
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise
    # print(url)
    originFileName = local_file_path.split("/").pop()
    fileMd5 = hashlib.md5(open(local_file_path, 'rb').read()).hexdigest()
    fileSize = str(os.path.getsize(local_file_path))
    res = request("POST","/v1/api/files/policy_callback",{"fileName":fileName,"originFileName":originFileName,"dir":dir,"endpoint":endpoint,"bucketName":bucket_name,"size":fileSize,"mimeType":extension,"fileMd5":fileMd5},token,device_info)
    # print(res)
    return res['data']['fileID'],fileName,extension,res['data']['ossPath']
    
    


def get_account_status(token ):
  device_info = request_device_info(token)
#   print(device_info)
  
  api_res = request("GET","/api/multimodal/video/processing",{},token,device_info)
#   print("processing", api_res)
  return api_res

# durationType: 1=6s  4=10s
# resolutionType: 1=760P 2=1080P 3=768P        
def gen_video(token,desc,file_path,model_id,type,durationType,resolutionType):
  
  device_info = request_device_info(token)
  print(device_info,"gen_video device_info")
  
  origin_url = None
  fileList = []
  if file_path:
    ali_res = request("GET","/v1/api/files/request_policy",{},token,device_info)
    print(ali_res)
    file_id,file_name,file_type,origin_url = upload_to_oss(ali_res['data']['accessKeyId'], ali_res['data']['accessKeySecret'], ali_res['data']['securityToken'], file_path, ali_res["data"]["endpoint"] , ali_res['data']['bucketName'],ali_res['data']['dir'],token,device_info)
    fileList.append({"id":file_id,"name":file_name,"type":file_type})
    print(fileList,"fileList")
    # 3:subject reference
    if type == 3:
      subject_detect_res = request("POST","/v2/api/multimodal/subject/detect",{"fileID":file_id},token,device_info)
      if subject_detect_res['statusInfo']['code'] != 0:
        # print(subject_detect_res)
        return subject_detect_res,origin_url
    # {"desc":"","useOriginPrompt":false,"fileList":[{"id":"303172732407775240","name":"4adea3b6-3ed8-47ea-b96c-a360a2ad21c6.png","type":"png"}]}
  res = request("POST", "/api/multimodal/generate/video", {"desc":desc,"useOriginPrompt":False,"fileList":fileList,"modelID":model_id, "quantity": "1", "durationType": durationType, "resolutionType": resolutionType}, token, device_info)
  print("gen_video res",res)
  return res, origin_url

def gen_image(token, desc, model_id, aspect_ratio, quantity):
    device_info = request_device_info(token)
    print(device_info, "gen_image device_info")

    res = request("POST", "/v1/api/multimodal/generate/image", {
        "desc": desc,
        "useOriginPrompt": False,
        "modelID": model_id,
        "aspectRatio": aspect_ratio,
        "quantity": str(quantity)
    }, token, device_info)
    print("gen_image res", res)
    return res


def get_user_info(token):
  device_info = request_device_info(token)
  res = request("GET", "/v1/api/user/info", {}, token, device_info)
#   print(res)
  return res

# status: 12,message: "Optimizing prompt in progress..."
# status: 1, message: "Video generation is in progress. Exiting will not halt  video's creation process."
# status: 2, 生成成功
# status: 14,message: "There is an issue with the text content, try using different content"
# status: 7, message: "Failure to pass the review."
# status: 22,message: "Account banned, unbanned by 2025-02-18 09:35:58.",
# status: 3, message: "The content generation has failed. Please try again."
# batch_type: 0:视频，1：图片
def get_video_status(token, batch_id, batch_type):
  device_info = request_device_info(token)
  print(device_info,"get_video_status device_info")
  params = {}
  if (batch_id != 0):
    params = {"batchInfoList":[{"batchID":batch_id, "batchType": batch_type}]}
  res = request("POST",'/v4/api/multimodal/video/processing', params, token, device_info)
  # print(res)
  return res
  
def cancel_video(token, video_id):
    device_info = request_device_info(token)
    print(device_info, "cancel_video device_info")
    res = request("POST", "/api/multimodal/video/cancel", {"videoID": video_id}, token, device_info)
    # print(res)
    return res 
  
def delete_video(token, video_id):
    device_info = request_device_info(token)
    print(device_info, "delete_video device_info")
    res = request("POST", "/v2/api/multimodal/video/delete", {"videoID": video_id}, token, device_info)
    # print(res)
    return res 

def read_task(token, videoList):
    device_info = request_device_info(token)
    print(device_info, "read_task device_info")
    res = request("POST", "/v1/api/multimodal/task/read", {"videoList": videoList}, token, device_info)
    print(res)
    return res


if __name__ == "__main__":
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzYwNzQ1NDIsInVzZXIiOnsiaWQiOiIzMDY4NTE3NTc5MDI4ODQ4NjciLCJuYW1lIjoieGlhb2NodW4gaGUiLCJhdmF0YXIiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKTU9mRnlscTFzSVI0NXlQZW9fT0lYTVBmY2FtZjVjc2tfT3dKMzRBaTBZQlczMkE9czk2LWMiLCJkZXZpY2VJRCI6IiIsImlzQW5vbnltb3VzIjpmYWxzZX19.RORVLdtkmomgO4g14LeMUwkLlWtifX8U_ka-1vKQWvk"
    
    # res, origin_url = gen_video(token, "a beautiful japan woman see me suddenly, and run to me happy, POV", "", "23010", 1, 1,1)
    # res, origin_url = gen_video(token, "jump", "images/1.png", "23102", 2, 1, 1)
    # res, origin_url = gen_video(token, "jump", "images/2.png", "23021", 3)
    # res, origin_url = gen_video(token, "a beautiful japan woman see me suddenly, and run to me happy, POV", "", "23200", 4,1,1)
    # print(res, origin_url)

    # res = gen_image(token, "a sexy woman", "image-01", "16:9")

    # delete_video(token, "350482372637220873")

    # res = get_video_status(token, "381768933798420485", 0)
    # print(res)
    
    # cancel_res = cancel_video(token, "342659447560282116")

    # res = get_user_info(token)
    # print(res)
    
    # res =  request_device_info(token)
    # print(res)
    # res = get_account_status(token)
    # print(res)
    # res =  gen_video(token, "")
    # print(res)
    
    
    # device_info = request_device_info(token)
    # print(device_info)
    
    # # res  = get_video_status(token,device_info, "303231293113155586")
    # # print(res)
    
    
    # res = gen_video(token, "女孩","images/2024-11-26/d7808681-ce04-460c-bf41-bb37a0367fe6.png")
    # print(res)
    
    # res = request("GET","/v1/api/files/request_policy",{},token,device_info)
    # print(res)
    
    # file_path = "/Users/hxc/auto_video/test.jpg"
    # url = upload_to_oss(res['data']['accessKeyId'], res['data']['accessKeySecret'], res['data']['securityToken'], file_path, res["data"]["endpoint"] , res['data']['bucketName'],res['data']['dir'],token,device_info)
    # print(url)
    
    