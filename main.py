import time
import json
from fastapi import FastAPI
from starlette.responses import PlainTextResponse
from weChat.tool import get_weChat_access_token
import requests

"""
    引用 FastAPI 函数
"""
from weChat.tool import get_weChat_access_token

app = FastAPI()


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

@app.get("/getapprovalinfo")
async def getapprovalinfo():

    url = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={app.state.access_token}'
    now = int(time.time())
    start = now - 7 * 24 * 60 * 60

    approvals = []
    next_cursor = ""

    while True:
        data = {
            "starttime": start,
            "endtime": now,
            "new_cursor": next_cursor,  # 注意是 cursor，不是 new_cursor
            "size": 100  # 最大 100
        }

        response = requests.post(url, json=data).json()

        print(response)

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
        if str(response2.json()['info']['sp_name']) in "采购申请单":
            response2Arr.append(response2.json())


    # 保存 JSON 文件
    with open("./data.json", "w", encoding="utf-8") as f:
        json.dump(response2Arr, f, ensure_ascii=False, indent=4)

