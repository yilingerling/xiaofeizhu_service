import asyncio
import json
import random
import time
import uuid
import os
from datetime import datetime, timedelta
import requests
import fdb
from fastapi import FastAPI, HTTPException,Query
from pydantic import BaseModel
from typing import List
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

"""
    创建 fastapi 实例
"""
from weChat.tool import get_weChat_access_token, send_approval_alert, get_name, get_userid_to_name

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或 ["*"] 允许所有
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取当前用户桌面路径
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop/xiaofeizhuImage")
# 挂载静态目录
app.mount("/static", StaticFiles(directory=desktop_path), name="static")


db_file = r"C:\Firebird_DB\my_db.fdb"  # 纯文件路径
db_path = f"localhost:{db_file}"       # DSN

if not os.path.exists(db_file):
    fdb.create_database(
        dsn=db_path,
        user='SYSDBA',
        password='xiaofeizhu'
    )

"""
    数据库连接
"""
def get_db_connection():
    con = fdb.connect(
        dsn=db_path,
        user='SYSDBA',
        password='xiaofeizhu'
    )
    return con

"""
    项目启动时自动调用 存进本地缓存
"""
@app.on_event("startup")
async def startup_event():
    token = await get_weChat_access_token()
    app.state.access_token = token

"""
    根路径
"""
@app.get("/")
async def root():

    return "RkQ6AjqTeAApB2BK"



"""
    普通用户 获取数据
"""
class Getappdata(BaseModel):
    current_page: int
    starttime: int
    endtime: int
    template_id: str
    sp_status: str
    user_id: str
    token: str
@app.post("/getapprovalinfo")
async def getapprovalinfo(getappdata:Getappdata):
    if await get_token(getappdata.user_id, getappdata.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:

        url = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={app.state.access_token}'
        # 存储编号
        approvals = []
        next_cursor = ""

        while True:
            data = {
                "starttime": int(getappdata.starttime),
                "endtime":  int(getappdata.endtime),
                "new_cursor": next_cursor,
                "size": 9999,  # 最大 100
                "filters": [
                    {
                        "key": "template_id",
                        "value": getappdata.template_id
                    },
                    {
                        "key": "sp_status",
                        "value": getappdata.sp_status
                    }
                ]
            }
            response = requests.post(url, json=data).json()
            approvals.extend(response.get("sp_no_list", []))

            next_cursor = response.get("new_next_cursor", "")
            if not next_cursor:
                break

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        # 存储结构
        response2Arr = []
        page_size = 20 # 每次返回的数据总量
        start = (int(getappdata.current_page) - 1) * page_size
        end = int(getappdata.current_page) * page_size

        for item in approvals[start:end]:
            url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={app.state.access_token}'
            data2 = {"sp_no": item}
            response2 = requests.post(url2, json=data2)

            response2Arr.append(response2.json())
        # 最后统一翻转数组
        response2Arr.reverse()

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        # 查询权限
        con = get_db_connection()
        cur = con.cursor()

        # 查询 xfzadmin 用户
        cur.execute("SELECT ACCOUNT_PERMISSION,COLUMN_PERMISSION,USERNAME FROM XFZUSERS WHERE ID = ?", (getappdata.user_id,))
        row = cur.fetchone()

        if row is None:
            return {
                "code": 404,
                "message": "未找到用户权限信息",
                "data": []
            }

        ACCOUNT_PERMISSION, COLUMN_PERMISSION,USERNAME = row



        # 获取映射 userid to username
        userid_to_name = await get_userid_to_name(app.state.access_token)

        # 再次赋值
        USERNAME = userid_to_name[0].get(USERNAME,"")

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        response3Arr = []

        if USERNAME == "WuFan" or getappdata.template_id == "C4WpQo3ea7rQP94wTQsKznpp4kir1ZczvjDtcPSF3" or getappdata.template_id == "C4WpQo3ea7rQP94wTQsKznpp4kir1aNegvUucTbBg":
            response3Arr = response2Arr
        else:

            for item in response2Arr:

                # 存储所有符合审批中的审批人
                users_id = []
                # 审批状态 1 审批中 2 已通过 3 已驳回
                sp_status = item['info']['sp_status']
                # 销售类型
                sales_type = item['info']['apply_data']['contents'][0]
                # 所有审批人信息
                node_list = item['info']['process_list']['node_list']

                # 审批中
                if sp_status == 1 and getappdata.sp_status == "1":
                    # 遍历所有审批流
                    for node in node_list:
                        # 当前审批流状态等于审批中
                        if node.get('sp_status') == 1:
                            # 当前审批流状态等于审批中 进入 遍历所有审批人
                            for sub_node in node['sub_node_list']:
                                # 当前审批流状态等于审批中 进入 遍历所有审批人 当前审批人等于 审批中
                                if sub_node.get('sp_yj') == 1:
                                    users_id.append(sub_node['userid'])

                # 审批中
                elif sp_status == 2 and getappdata.sp_status == "2":
                    # 遍历所有审批流
                    for node in node_list:
                        # 当前审批流状态等于审批中
                        if node.get('sp_status') == 2:
                            # 当前审批流状态等于审批中 进入 遍历所有审批人
                            for sub_node in node['sub_node_list']:
                                # 当前审批流状态等于审批中 进入 遍历所有审批人 当前审批人等于 审批中
                                if sub_node.get('sp_yj') == 2 or sub_node.get('sp_yj') == 14 or sub_node.get('sp_yj') == 15 or sub_node.get('sp_yj') == 13:
                                    users_id.append(sub_node['userid'])
                        if node.get('node_type') == 2:
                            # 如果等于 2 则 添加该流程块所有人员
                            for sub_node in node['sub_node_list']:
                                    users_id.append(sub_node['userid'])

                # 判断 userid 与 销售权限
                if USERNAME in users_id:
                    if sales_type == "采购销售" and json.loads(ACCOUNT_PERMISSION)[0]:
                        response3Arr.append(item)

                    elif sales_type == "囤货销售" and json.loads(ACCOUNT_PERMISSION)[1]:
                        response3Arr.append(item)

                    elif sales_type not in ["采购销售", "囤货销售"] and json.loads(ACCOUNT_PERMISSION)[2]:
                        response3Arr.append(item)

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        # 对应 映射表 修改 数据 审批人姓名
        for item in response3Arr:
            item['info']['applyer']['userid'] =  userid_to_name[1].get(item['info']['applyer']['userid'],"")

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        return {
            "code": 200,
            "total":len(approvals),
            "data": response3Arr,
            "ACCOUNT_PERMISSION":ACCOUNT_PERMISSION,
            "COLUMN_PERMISSION":COLUMN_PERMISSION,
            "message": "成功",
        }


"""
    根据图片ID数组获取图片
"""
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
            with open(f"{desktop_path}/{item}.jpg", "wb") as f:
                f.write(response.content)
            # print("图片已保存为 downloaded_image.jpg")
        else:
            print("请求失败，状态码：", response.status_code)
            print("响应内容：", response.text)
        responseImagesArr.append(f"https://xiaofeizhu.chat/api/static/{item}.jpg")
    return responseImagesArr

"""
    删除所有下载的图片
"""
def clear_static_folder():
    for filename in os.listdir(desktop_path):
        file_path = os.path.join(desktop_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或符号链接
            elif os.path.isdir(file_path):
                # 如果静态文件夹里还有子目录，递归删除
                import shutil
                shutil.rmtree(file_path)
            # print(f"已删除: {file_path}")
        except Exception as e:
            print(f"删除失败 {file_path}，原因: {e}")

"""
    查询 Token 信息（通过 user_id）
"""
async def get_token(user_id: int, token: str):
    con = get_db_connection()
    cur = con.cursor()

    cur.execute("SELECT token, create_time FROM xfztoken WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if not row:
        con.close()
        raise HTTPException(status_code=404, detail="Token 不存在")

    db_token, create_time = row

    # 判断是否超过8小时
    is_expired = create_time < datetime.now() - timedelta(hours=8)

    if db_token != token and is_expired:
        # 删除 token 记录
        cur.execute("DELETE FROM xfztoken WHERE user_id = ?", (user_id,))
        con.commit()
        con.close()
        return True
    else:
        con.close()
        return False


"""
    管理员登录（针对 xfzadmin 表）
"""
class LoginData(BaseModel):
    username: str
    password: str
@app.post("/admin/login")
async def admin_login(data: LoginData):

    username = data.username
    password = data.password

    con = get_db_connection()
    cur = con.cursor()

    # 查询 xfzadmin 用户
    cur.execute("SELECT ID, PASSWORD FROM xfzadmin WHERE USERNAME = ?", (username,))
    row = cur.fetchone()

    if not row:
        con.close()
        raise HTTPException(status_code=400, detail="用户名不存在")

    user_id, db_password = row
    if db_password != password:
        con.close()
        raise HTTPException(status_code=400, detail="密码错误")

    # 生成 token
    new_uuid = uuid.uuid4().hex
    timestamp = int(time.time())
    random_digit = random.randint(0, 9)
    token_str = f"{new_uuid}{user_id}{timestamp}{random_digit}"

    create_time = datetime.now()
    # 先查有没有这个 user_id
    cur.execute("SELECT 1 FROM xfztoken WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()

    if exists:
        # 更新
        cur.execute(
            "UPDATE xfztoken SET token = ?, create_time = ? WHERE user_id = ?",
            (token_str, create_time, user_id)
        )
    else:
        # 插入
        cur.execute(
            "INSERT INTO xfztoken (user_id, token, create_time) VALUES (?, ?, ?)",
            (user_id, token_str, create_time)
        )
    con.commit()
    con.close()

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "user_id": user_id,
            "user_name": username,
            "token": token_str
        }
    }


"""
    普通用户登录
"""
@app.post("/user/login")
async def user_login(data: LoginData):
    username = data.username
    password = data.password

    con = get_db_connection()
    cur = con.cursor()

    # 查询 xfzadmin 用户
    cur.execute("SELECT ID, PASSWORD FROM XFZUSERS WHERE USERNAME = ?", (username,))
    row = cur.fetchone()

    if not row:
        con.close()
        raise HTTPException(status_code=400, detail="用户名不存在")

    user_id, db_password = row
    if db_password != password:
        con.close()
        raise HTTPException(status_code=400, detail="密码错误")

    # 生成 token
    new_uuid = uuid.uuid4().hex
    timestamp = int(time.time())
    random_digit = random.randint(0, 9)
    token_str = f"{new_uuid}{user_id}{timestamp}{random_digit}"

    create_time = datetime.now()
    # 先查有没有这个 user_id
    cur.execute("SELECT 1 FROM xfztoken WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()

    if exists:
        # 更新
        cur.execute(
            "UPDATE xfztoken SET token = ?, create_time = ? WHERE user_id = ?",
            (token_str, create_time, user_id)
        )
    else:
        # 插入
        cur.execute(
            "INSERT INTO xfztoken (user_id, token, create_time) VALUES (?, ?, ?)",
            (user_id, token_str, create_time)
        )

    con.commit()
    con.close()

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "user_id": user_id,
            "user_name": username,
            "token": token_str
        }
    }

"""
    管理员 添加普通用户账号
"""
class UserCreate(BaseModel):
    username: str
    password: str
@app.post("/admin/add_user")
async def add_user(data: UserCreate):

    username = data.username
    password = data.password

    user_id = uuid.uuid4().hex

    account_permission = [False] * 3
    column_permission = {
        "订单编号": True,
        "销售类型": True,
        "商品名称": True,
        "上架原商品是否还在": False,
        "商品来源": False,
        "商品编码及商家名称": False,
        "商家销售价格": False,
        "到手港币金额": False,
        "销售日期": False,
        "销售截至日期": False,
        "商品瑕疵": False,
        "配件": False,
        "上架商品图片": False,
        "销售订单截图": False,
        "运输面单截图": False,
        "申请人": False,
        "审批类型": False,
        "审批状态": False
    }

    con = get_db_connection()
    cur = con.cursor()

    # 检查用户名是否已存在
    cur.execute("SELECT 1 FROM xfzusers WHERE username = ?", (username,))
    if cur.fetchone():
        con.close()
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 插入新用户
    cur.execute("""
        INSERT INTO xfzusers (id, username, password, account_permission, column_permission)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        password,
        json.dumps(account_permission),   # 转换为 JSON 字符串
        json.dumps(column_permission)
    ))

    con.commit()
    con.close()

    return {
        "code": 200,
        "message": "用户添加成功",
        "data": {
            "user_id": user_id,
            "username": username
        }
    }


"""
    管理员 查询全部用户
"""
class UserGet(BaseModel):
    user_id: str
    token: str
@app.post("/admin/get_user")
async def get_user(data: UserGet):

    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:
        con = get_db_connection()
        cur = con.cursor()

        # 检查用户名是否已存在
        cur.execute("SELECT * FROM xfzusers")
        row = cur.fetchall()

        users = []
        for row in row:
            users.append({
                "user_id": row[0],
                "username": row[1],
                "password": row[2],
                "account_permission": json.loads(row[3].replace("false", "false").replace("true", "true")),
                # 保险起见处理布尔大小写
                "column_permission": json.loads(row[4].replace("false", "false").replace("true", "true"))
            })

        return {
            "code": 200,
            "message": "查询成功",
            "data": users
        }


class Userdel(BaseModel):
    user_id: str
    token: str
    deluser_id:str

"""
    删除用户
"""
@app.post("/admin/del_user")
async def del_user(data: Userdel):
    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
           DELETE FROM XFZUSERS WHERE ID = ?
        """, (data.deluser_id,))

        con.commit()
        con.close()

        return {
            "code": 200,
            "message": "删除成功",
            "data": True
        }

"""
    管理员 修改用户信息加权限
"""
class GetPERMISSION(BaseModel):
    user_id: str
    token: str
    UPuserid:str
    USERNAME:str
    PASSWORD:str
    ACCOUNT_PERMISSION:str
    COLUMN_PERMISSION:str
@app.post("/admin/getUserUP")
async def getUserUP(getPERMISSION:GetPERMISSION):
    if await get_token(getPERMISSION.user_id, getPERMISSION.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:

        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
           UPDATE XFZUSERS a
                SET
                    a.USERNAME = ?,
                    a.PASSWORD = ?,
                    a.ACCOUNT_PERMISSION = ?,
                    a.COLUMN_PERMISSION = ?
                WHERE
                    a.ID = ?

        """, (getPERMISSION.USERNAME,getPERMISSION.PASSWORD,getPERMISSION.ACCOUNT_PERMISSION,getPERMISSION.COLUMN_PERMISSION,getPERMISSION.UPuserid))

        con.commit()

        con.close()

        return {
            "code": 200,
            "message": "修改成功",
            "data": True
        }


"""
    消息推送
"""
async def approval_check():
    print(f"[{datetime.now()}] 执行审批检查")
    try:
        token = app.state.access_token
        now = int(time.time())
        one_month_ago = now - 30 * 86400

        approvals = []
        next_cursor = ""

        url = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={token}'

        while True:
            data = {
                "starttime": one_month_ago,
                "endtime": now,
                "new_cursor": next_cursor,
                "size": 9999,
                "filters": [
                    {
                        "key": "template_id",
                        "value": "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE"
                    },
                    {
                        "key": "sp_status",
                        "value": "1"
                    }
                ]
            }

            response = requests.post(url, json=data).json()
            approvals.extend(response.get("sp_no_list", []))
            next_cursor = response.get("new_next_cursor", "")
            if not next_cursor:
                break

        response2Arr = []
        for item in approvals:
            url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={token}'
            data2 = {"sp_no": item}
            response2 = requests.post(url2, json=data2)
            response2Arr.append(response2.json())

        response2Arr.reverse()

        for item in response2Arr:
            for node in item.get("info", {}).get("process_list", {}).get("node_list", []):
                if node.get("sp_status") == 1:

                    Date0 = ""
                    Date1 = ""
                    name = ""

                    for content in item['info']['apply_data']['contents']:
                        for t in content.get("title", []):
                            text = t.get("text", "")
                            if text == "销售日期":
                                Date0 = content["value"]['date']['s_timestamp']
                            elif text == "销售截至日期":
                                Date1 = content["value"]['date']['s_timestamp']
                            elif text == "商品名称":
                                name = content["value"]['text']
                        if Date0 and Date1 and name:
                            break

                    if not Date0 or not Date1:
                        continue

                    hours_diff = (int(Date1) - int(Date0)) / 3600

                    if hours_diff < 48:
                        for sub_node in node.get('sub_node_list', []):
                            touser = sub_node.get('userid')
                            content = (
                                f"订单号：{item['info']['sp_no']}\n"
                                f"发起人：{await get_name(token, item['info']['applyer']['userid'])}\n"
                                f"审批人：{touser}\n"
                                f"商品名称：{name}\n"
                                f"销售日期：{datetime.fromtimestamp(int(Date0)).strftime('%Y-%m-%d')}\n"
                                f"销售截止日期：{datetime.fromtimestamp(int(Date1)).strftime('%Y-%m-%d')}\n"
                                f"状态：审批即将超时,请处理"
                            )

                            await send_approval_alert(touser,token,content)

                            time.sleep(1)


    except Exception as e:
        print("审批轮询错误：", e)
"""
    消息推送 每到双数 整点 发送消息
"""
async def wait_until_next_2_hour_mark():
    now = datetime.now()
    # 计算当前时间对应的2小时整点，比如0,2,4...22点
    next_hour = (now.hour // 2 + 1) * 2
    if next_hour >= 24:
        # 如果超过24点，转到第二天0点
        next_run = now.replace(day=now.day + 1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)

    wait_seconds = (next_run - now).total_seconds()
    print(f"等待 {wait_seconds} 秒，到下一个2小时整点: {next_run}")
    await asyncio.sleep(wait_seconds)

# 测试 时间 每分钟发一个
# async def wait_until_next_2_hour_mark():
#     now = datetime.now()
#     next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
#     wait_seconds = (next_run - now).total_seconds()
#     print(f"等待 {wait_seconds} 秒，到下一分钟整点: {next_run}")
#     await asyncio.sleep(wait_seconds)
"""
    消息推送 定时循环
"""
async def approval_check_loop():
    while True:
        await wait_until_next_2_hour_mark()
        await approval_check()
"""
    消息推送 项目启动后再启动
"""
@app.on_event("startup")
async def startup_event():
    app.state.access_token = await get_weChat_access_token()
    asyncio.create_task(approval_check_loop())


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080, reload=False)
