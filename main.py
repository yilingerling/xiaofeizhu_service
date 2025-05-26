import time
from typing import List
import json
from fastapi import FastAPI,Query
from pydantic import BaseModel
from starlette.responses import PlainTextResponse
import requests
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
import os
"""
    引用 FastAPI 函数lijiaao
"""
from weChat.tool import get_weChat_access_token



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或 ["*"] 允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/images", StaticFiles(directory="static/images"), name="images")
"""
    项目启动时自动调用 存进本地缓存
"""
@app.on_event("startup")
async def startup_event():
    token = await get_weChat_access_token()
    app.state.access_token = token

@app.get("/", response_class=PlainTextResponse)
async def root():
    # return {"令牌": app.state.access_token}
    return "RkQ6AjqTeAApB2BK"

@app.get("/getapprovalinfo/")
async def getapprovalinfo(starttime: str,endtime: str,template_id: str):
    # print(starttime)
    # print(endtime)
    # print(template_id)
    url = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={app.state.access_token}'
    approvals = []
    next_cursor = ""
    while True:
        data = {
            "starttime": int(starttime),
            "endtime":  int(endtime),
            "new_cursor": next_cursor,  # 注意是 cursor，不是 new_cursor
            "size": 100,  # 最大 100
            "filters": [
                {
                    "key": "template_id",
                    "value": template_id
                }
            ]
        }
        response = requests.post(url, json=data).json()
        # print(response)
        approvals.extend(response.get("sp_no_list", []))

        next_cursor = response.get("new_next_cursor", "")
        if not next_cursor:
            break

    response2Arr = []

    # 方法2: 使用for循环
    for item in approvals:

        url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={app.state.access_token}'

        data2 = {
            "sp_no": item
        }

        response2 = requests.post(url2, json=data2)
        # print(response2.json()['info']['sp_name'],response2.json()['info']['template_id'])
        # if str(response2.json()['info']['sp_name']) in "采购报销单":
        response2Arr.append(response2.json())
         # print(response2.json()['info']['sp_name'], response2.json()['info']['template_id'])
    # print(response2Arr[0])

    # 保存 JSON 文件
    with open("./data.json", "w", encoding="utf-8") as f:
        json.dump(response2Arr, f, ensure_ascii=False, indent=4)

    return {
            "code":200,
            "data":response2Arr,
            "message": "成功",
           }

@app.get("/getPicture/")
async def getPicture(media_ids: List[str] = Query(alias="media_ids[]")):
    clear_static_folder()
    responseImagesArr = []
    for item in media_ids:
        # 构建请求 URL
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={app.state.access_token}&media_id={item}"
        # 发起 GET 请求
        response = requests.get(url)
        # 检查响应状态
        if response.status_code == 200:
            # 将图片保存到本地
            with open(f"static/images/{item}.jpg", "wb") as f:
                f.write(response.content)
            print("图片已保存为 downloaded_image.jpg")
        else:
            print("请求失败，状态码：", response.status_code)
            print("响应内容：", response.text)
        responseImagesArr.append(f"http://localhost:8080/images/{item}.jpg")
    return responseImagesArr

"""
删除所有下载的图片
"""
def clear_static_folder():
    for filename in os.listdir('static/images'):
        file_path = os.path.join('static/images', filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或符号链接
            elif os.path.isdir(file_path):
                # 如果静态文件夹里还有子目录，递归删除
                import shutil
                shutil.rmtree(file_path)
            print(f"已删除: {file_path}")
        except Exception as e:
            print(f"删除失败 {file_path}，原因: {e}")