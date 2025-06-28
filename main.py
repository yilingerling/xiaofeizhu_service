import asyncio
import base64
import json
import random
import uuid
import os
import requests
import fdb
import uvicorn
import time  # 用于 time.time()

from pathlib import Path
from fastapi import FastAPI, HTTPException,Query
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from datetime import datetime, date, time as dt_time, timedelta  # 避免冲突

""" 创建 fastapi 实例 """
from weChat.tool import get_weChat_access_token, send_approval_alert, get_name, get_userid_to_name, clear_static_folder, \
    order_exists, insert_json_to_firebird

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# if not os.path.exists(db_file):
#     fdb.create_database(
#         dsn=db_path,
#         user='SYSDBA',
#         password='xiaofeizhu'
#         password='123456'
#     )

""" 数据库连接 """
def get_db_connection():

    con = fdb.connect(
        dsn=db_path,
        user='SYSDBA',
        password='123456'

    )

    return con

""" 项目启动时自动调用 存进本地缓存 """
@app.on_event("startup")
async def startup_event():
    token = await get_weChat_access_token()
    app.state.access_token = token

""" 根路径 """
@app.get("/")
async def root():
    return "RkQ6AjqTeAApB2BK"





















"""""""""""""""
普通用户 获取数据
"""""""""""""""
class Getappdata(BaseModel):
    current_page: int
    starttime: int
    endtime: int
    template_id: str
    sp_status: str
    user_id: str
    token: str
@app.post("/getapprovalinfo")
async def get_approval_info(getappdata:Getappdata):

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

        # 最后统一翻转数组
        approvals.reverse()

        for item in approvals[start:end]:
            url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={app.state.access_token}'
            data2 = {"sp_no": item}
            response2 = requests.post(url2, json=data2)
            time.sleep(0.3)
            response2Arr.append(response2.json())


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

        cur.execute('SELECT USERNAME, ROLE FROM XFZUSERS WHERE ID = ?', (getappdata.user_id,))
        row = cur.fetchone()

        if not row:
            return {
                "code": 404,
                "message": "该用户不存在",
                "data": [],
                "total": 0
            }

        user_role = row[1]

        if user_role == "超级管理员":

            # 必须采购审批单 并且 审批中才有
            if getappdata.template_id == "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE" and getappdata.sp_status == "1":
                for item in response2Arr:
                    users_id = []  # 每个 item 独立存储审批人
                    user_str = ""

                    sp_status = item['info']['sp_status']
                    node_list = item['info']['process_list']['node_list']

                    if sp_status == 1 and getappdata.sp_status == "1":
                        found = False

                        for node in node_list:
                            if node.get('sp_status') == 1 and node.get('node_type') == 3:
                                for sub_node in node.get('sub_node_list', []):
                                    if sub_node.get('sp_yj') == 1:
                                        users_id.append(sub_node['userid'])
                                found = True
                                break

                        if not found:
                            for node in node_list:
                                if node.get('sp_status') == 1 and node.get('node_type') == 1:
                                    for sub_node in node.get('sub_node_list', []):
                                        if sub_node.get('sp_yj') == 1:
                                            users_id.append(sub_node['userid'])
                                    break

                    # 拼接 user_str（改为每条 item 单独处理）
                    for i, user in enumerate(users_id):
                        name = userid_to_name[1].get(user, "")
                        if i == 0:
                            user_str += name
                        else:
                            user_str += "、" + name

                    item["user_str"] = user_str  # 添加字段
            else:
                # 处理审批人（谁通过的，谁驳回的）
                for item in response2Arr:

                    # 已通过审批人
                    user_sp_status_2 = ""
                    # 已驳回审批人
                    user_sp_status_3 = ""

                    sp_status = item['info']['sp_status']
                    node_list = item['info']['process_list']['node_list']

                    if sp_status == 2 and getappdata.sp_status == "2":

                        for node in node_list:
                            if node.get('sp_status') == 2 and node.get('node_type') == 1:
                                for sub_node in node.get('sub_node_list', []):
                                    if sub_node.get('sp_yj') == 2:
                                        user_sp_status_2 = sub_node['userid']


                        item["user_sp_status_2"] = userid_to_name[1].get(user_sp_status_2, "")  # 添加字段

                    if sp_status == 3 and getappdata.sp_status == "3":

                        for node in node_list:
                            if node.get('sp_status') == 3 and node.get('node_type') == 1:
                                for sub_node in node.get('sub_node_list', []):
                                    if sub_node.get('sp_yj') == 3:
                                        user_sp_status_3 = sub_node['userid']

                        item["user_sp_status_3"] = userid_to_name[1].get(user_sp_status_3, "")  # 添加字段

            response3Arr = response2Arr
        elif user_role == "发货员" and getappdata.template_id == "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE" and getappdata.sp_status == "1":
            for item in response2Arr:
                users_id = []  # 每个 item 独立存储审批人
                user_str = ""

                sp_status = item['info']['sp_status']
                node_list = item['info']['process_list']['node_list']

                if sp_status == 1 and getappdata.sp_status == "1":
                    found = False

                    for node in node_list:
                        if node.get('sp_status') == 1 and node.get('node_type') == 3:
                            for sub_node in node.get('sub_node_list', []):
                                if sub_node.get('sp_yj') == 1:
                                    users_id.append(sub_node['userid'])
                            found = True
                            break

                    if not found:
                        for node in node_list:
                            if node.get('sp_status') == 1 and node.get('node_type') == 1:
                                for sub_node in node.get('sub_node_list', []):
                                    if sub_node.get('sp_yj') == 1:
                                        users_id.append(sub_node['userid'])
                                break

                # 拼接 user_str（改为每条 item 单独处理）
                for i, user in enumerate(users_id):
                    name = userid_to_name[1].get(user, "")
                    if i == 0:
                        user_str += name
                    else:
                        user_str += "、" + name

                item["user_str"] = user_str  # 添加字段

            response3Arr = response2Arr

        else:

            for item in response2Arr:

                # 存储所有符合审批中的审批人
                users_id = []
                # 审批状态 1 审批中 2 已通过 3 已驳回
                sp_status = item['info']['sp_status']
                # 销售类型
                sales_type = item['info']['apply_data']['contents'][0]['value']['selector']['options'][0]['value'][0]['text']
                # 所有审批人信息
                node_list = item['info']['process_list']['node_list']
                # 发起人id
                userid = item['info']['applyer']['userid']

                # 审批中
                if sp_status == 1 and getappdata.sp_status == "1":

                    # 把发起人放进去
                    users_id.append(userid)

                    # 是否已找到审批人标记
                    found = False

                    # 第一步：优先处理 node_type == 3
                    for node in node_list:
                        if node.get('sp_status') == 1 and node.get('node_type') == 3:
                            for sub_node in node.get('sub_node_list', []):
                                if sub_node.get('sp_yj') == 1:
                                    users_id.append(sub_node['userid'])
                            found = True
                            break  # 找到优先级为3的审批流后停止遍历

                    # 第二步：若没有找到 node_type == 3 的审批人，尝试 node_type == 1
                    if not found:
                        for node in node_list:
                            if node.get('sp_status') == 1 and node.get('node_type') == 1:
                                for sub_node in node.get('sub_node_list', []):
                                    if sub_node.get('sp_yj') == 1:
                                        users_id.append(sub_node['userid'])
                                break

                # 已通过
                elif sp_status == 2 and getappdata.sp_status == "2":

                    # 把 发起人 申请人 放进去
                    users_id.append(userid)

                    # 这里不break了 因为他之前审批人流程错了 所以两个审批人流程 所以无法判断谁是第一个审批人所以只能全部遍历
                    for node in node_list:
                        if node.get('sp_status') == 2 and node.get('node_type') == 1:
                            for sub_node in node.get('sub_node_list', []):
                                if sub_node.get('sp_yj') == 2:
                                    users_id.append(sub_node['userid'])

                    item["user_sp_status_2"] = userid_to_name[1].get(users_id[0], "")  # 添加字段

                # 已驳回
                elif sp_status == 3 and getappdata.sp_status == "3":

                    # 把发起人放进去
                    users_id.append(userid)

                    # 这里不break了 因为他之前审批人流程错了 所以两个审批人流程 所以无法判断谁是第一个审批人所以只能全部遍历
                    for node in node_list:
                        if node.get('sp_status') == 3 and node.get('node_type') == 1:
                            for sub_node in node.get('sub_node_list', []):
                                if sub_node.get('sp_yj') == 3:
                                    users_id.append(sub_node['userid'])

                    item["user_sp_status_3"] = userid_to_name[1].get(users_id[0], "")  # 添加字段

                # 判断 userid 与 销售权限
                if USERNAME in users_id and getappdata.template_id == "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE":

                    if sales_type == "采购销售" and json.loads(ACCOUNT_PERMISSION)[0]:
                        response3Arr.append(item)

                    if sales_type == "囤货销售" and json.loads(ACCOUNT_PERMISSION)[1]:
                        response3Arr.append(item)

                    if sales_type not in ["采购销售", "囤货销售"] and json.loads(ACCOUNT_PERMISSION)[2]:
                        response3Arr.append(item)
                elif USERNAME in users_id:
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

        print(f"--------请求日志--------\n"
              f"日期时间：{time.strftime("%Y-%m-%d %H:%M:%S")}\n"
              f"获取编号：{len(approvals)}条\n"
              f"取得数据：{len(response2Arr)}条\n"
              f"最终数据：{len(response3Arr)}条")

        return {
            "code": 200,
            "total":len(approvals),
            "data": response3Arr,
            "ACCOUNT_PERMISSION":ACCOUNT_PERMISSION,
            "COLUMN_PERMISSION":COLUMN_PERMISSION,
            "message": "成功",
        }










"""""""""""""""""""""""""""""""""吴帆 张建辉 朱紫嫣 吴涛 获取 表格数据 """""""""""""""""""""""""""""""""
class TableData(BaseModel):
    user_name:str
    user_id: str
    token:str
@app.post("/getTableData")
async def get_table_data(tableData:TableData):

    user_id = tableData.user_id
    token = tableData.token
    user_name = tableData.user_name

    if await get_token(user_id, token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:

        """========================================================================================================================="""
        """查询7天内数据"""
        """========================================================================================================================="""
        url = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={app.state.access_token}'
        # 存储编号
        approvals = []
        next_cursor = ""

        today_start = datetime.combine(date.today(), dt_time.min)
        seven_days_ago = today_start - timedelta(days=15)
        today_end = datetime.combine(date.today(), dt_time.max)

        for i in range(2):

            if i==1:
                while True:
                    data = {
                        "starttime":  int(seven_days_ago.timestamp()),
                        "endtime": int(today_end.timestamp()),
                        "new_cursor": next_cursor,
                        "size": 9999,  # 最大 100
                        "filters": [
                            {
                                "key": "template_id",
                                "value": "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE"
                            },
                            {
                                "key": "sp_status",
                                "value": "2"
                            }
                        ]
                    }
                    response = requests.post(url, json=data).json()

                    approvals.extend(response.get("sp_no_list", []))
                    next_cursor = response.get("new_next_cursor", "")
                    if not next_cursor:
                        break
            else:
                while True:
                    data = {
                        "starttime": int(seven_days_ago.timestamp()),
                        "endtime": int(today_end.timestamp()),
                        "new_cursor": next_cursor,
                        "size": 9999,  # 最大 100
                        "filters": [
                            {
                                "key": "template_id",
                                "value": "3WLtybSyYX6kpA5X1Ygx48DC7jz4QE4g7v1S2QmE"
                            },
                            {
                                "key": "sp_status",
                                "value": "3"
                            }
                        ]
                    }
                    response = requests.post(url, json=data).json()
                    approvals.extend(response.get("sp_no_list", []))

                    next_cursor = response.get("new_next_cursor", "")
                    if not next_cursor:
                        break


        """========================================================================================================================="""
        """开始执行 插入逻辑"""
        """========================================================================================================================="""
        # 开始数据库连接
        con = get_db_connection()
        cur = con.cursor()

        # 检查用户名是否已存在
        cur.execute("SELECT * FROM xfzusers")
        xfzusers = cur.fetchall()

        # 获取映射 userid to username
        userid_to_name = await get_userid_to_name(app.state.access_token)

        if os.path.exists("trash_bin.json"):
            with open("trash_bin.json", "r", encoding="utf-8") as f:
                try:
                    old_order_list = json.load(f)
                except json.JSONDecodeError:
                    old_order_list = []
        else:
            old_order_list = []

        # 遍历循环所有编号 对齐进行处理
        for approval in approvals:

            if not order_exists(cur, approval) and approval not in old_order_list:


                url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={app.state.access_token}'
                item = requests.post(url2, json={"sp_no": approval}).json()

                time.sleep(0.3)

                if item.get("errmsg") != "ok":
                    print(f"{approval} 已通过数据 查询失败")

                # 存储数据筛选出来的通过人ID
                successFlag_user_id = ""

                node_list = item['info']['process_list']['node_list']

                for node in node_list:
                    if node.get('sp_status') == 2 and node.get('node_type') == 1:
                        for sub_node in node.get('sub_node_list', []):
                            if sub_node.get('sp_yj') == 2:
                                successFlag_user_id = sub_node['userid']
                    elif node.get('sp_status') == 3 and node.get('node_type') == 1:
                        for sub_node in node.get('sub_node_list', []):
                            if sub_node.get('sp_yj') == 3:
                                successFlag_user_id = sub_node['userid']

                # 获取销售类型
                sp_name = item['info']['apply_data']['contents'][0]['value']['selector']['options'][0]['value'][0]['text']
                # 获取审批状态
                sp_status = str(item['info']['sp_status'])
                # 订单标号
                sp_no = item['info']['sp_no']

                # 获取销售截止日期
                for content in item['info']['apply_data']['contents']:

                    if content['title'][0]['text'] == "销售截至日期":

                        xs_jz_date = content['value']['date']['s_timestamp']

                # 当前数据属于谁
                data_user_name = userid_to_name[1].get(successFlag_user_id, "")

                # 创建要存储的对象信息
                item_data = {
                    # 审批人
                    "applyer": data_user_name,

                    "sp_name": sp_name,
                    "update_time": "无",
                    "sp_no": sp_no,
                    # 超链接
                    "link_url": "",
                    # 销售人名称
                    "xs_name": userid_to_name[1].get(item['info']['applyer']['userid'], ""),
                    # 审批状态
                    "sp_status": sp_status,
                    # 驳回原因
                    "reject_reason": "",
                    # 段小狸编码
                    "dxl_number": "",
                    # 商家名称
                    "merchant_name": "",
                    # 采购价格
                    "purchase_price": "",
                    # 付款日期
                    "payment_date": "",
                    # 支付方式
                    "payment_method": "",
                    # 是否直接发货
                    "is_direct_delivery": "",
                    # 快递单号
                    "tracking_number": "",
                    # 是否需要养护
                    "needs_maintenance": "",
                    # 养护人
                    "maintenance_person": "",
                    # 快递费
                    "shipping_fee": "",
                    # 养护内容
                    "maintenance_content": "",
                    # 养护价格
                    "maintenance_price": "",
                    # 是否结算
                    "is_settled": "",
                    # 销售截止日期
                    "sx_jz_date": xs_jz_date,
                    # 结算日期
                    "settlement_date": "",
                    # 是否发货
                    "is_shipped": ""
                }

                insert_json_to_firebird(cur,con,approval,item_data)

        """========================================================================================================================="""
        """ 最后一步，根据传来的用户ID 返回最终数据"""
        """========================================================================================================================="""

        try:
            # 初始化变量
            user_role = ""
            user_data = []
            db_user_name = ""

            cur.execute('SELECT USERNAME, ROLE FROM XFZUSERS WHERE ID = ?', (user_id,))
            row = cur.fetchone()
  
            if not row:
                return {
                    "code": 404,
                    "message": "该用户不存在",
                    "data": [],
                    "total": 0
                }

            db_user_name = row[0]
            user_role = row[1]

            # 2. 根据角色返回不同数据
            if db_user_name and user_role:

                cur.execute("SELECT OBJ_INFO FROM XFZTABLEDATA")
                rows = cur.fetchall()

                if user_role == "超级管理员" or user_role == "发货员":
                    # 只要 OBJ_INFO 这一列
                    user_data = [json.loads(row[0]) for row in rows]

                elif user_role == "采购员":
                    user_data = [
                        json.loads(row[0])
                        for row in rows
                        if json.loads(row[0]).get('applyer') == db_user_name
                    ]


                else:
                    return {
                        "code": 403,
                        "message": f"角色【{user_role}】无权限访问",
                        "data": [],
                        "total": 0
                    }

                return {
                    "code": 200,
                    "message": "查询成功",
                    "data": user_data,
                    "total": len(user_data)
                }

            else:
                return {
                    "code": 403,
                    "message": "当前角色无权限",
                    "data": [],
                    "total": 0
                }

        except Exception as e:
            print(f"❌ 发生错误：{e}")
            return {
                "code": 500,
                "message": f"服务错误：{e}",
                "data": [],
                "total": 0
            }
        finally:
            if 'cur' in locals():
                cur.close()










""" 删除表格数据 """
class DelTable(BaseModel):
    sp_no: str
    user_id:str
    token:str
TRASH_FILE = "trash_bin.json"
@app.post("/DELXFZTABLEDATA")
async def DELXFZTABLEDATA(data: DelTable):
    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }

    con = get_db_connection()
    cur = con.cursor()

    # 1️⃣ 删除数据库里的这个订单
    cur.execute(
        "DELETE FROM XFZTABLEDATA WHERE orderID = ?",
        (data.sp_no,)
    )
    con.commit()
    con.close()

    # 2️⃣ 记录到本地的 trash_bin.json
    trash_list = []

    # 如果文件存在就先读出来
    if os.path.exists(TRASH_FILE):
        with open(TRASH_FILE, "r", encoding="utf-8") as f:
            try:
                trash_list = json.load(f)
            except json.JSONDecodeError:
                trash_list = []

    # 追加
    trash_list.append(data.sp_no)

    # 保存回去
    with open(TRASH_FILE, "w", encoding="utf-8") as f:
        json.dump(trash_list, f, ensure_ascii=False, indent=2)

    return {
        "code": 200,
        "message": "删除成功，并已记录到垃圾桶",
        "data": True
    }

""" 表格 添加一行数据 """
class AddTableData(BaseModel):
    sp_no:str
    user_id:str
    token:str
@app.post("/add_table_data_one_cow")
async def Add_table_data(data: AddTableData):
    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:
        con = get_db_connection()
        cur = con.cursor()

        item_data = {
            "sp_name": "",
            "update_time": "无",
            "sp_no": data.sp_no,
            # 超链接
            "link_url": "",
            # 销售人名称
            "xs_name": "",
            # 审批状态
            "sp_status": "",
            # 驳回原因
            "reject_reason": "",
            # 段小狸编码
            "dxl_number": "",
            # 商家名称
            "merchant_name": "",
            # 采购价格
            "purchase_price": "",
            # 付款日期
            "payment_date": "",
            # 支付方式
            "payment_method": "",
            # 是否直接发货
            "is_direct_delivery": "",
            # 快递单号
            "tracking_number": "",
            # 是否需要养护
            "needs_maintenance": "",
            # 养护人
            "maintenance_person": "",
            # 快递费
            "shipping_fee": "",
            # 养护内容
            "maintenance_content": "",
            # 养护价格
            "maintenance_price": "",
            # 是否结算
            "is_settled": "",
            # 销售截止日期
            "sx_jz_date":"",
            # 结算日期
            "settlement_date": "",
            # 是否发货
            "is_shipped": ""
        }

        insert_json_to_firebird(cur, con, data.sp_no, item_data)

        con.commit()
        con.close()

        return {
            "code": 200,
            "message": "添加成功",
            "data": True
        }

""" 修改用户表格数据得内容 """
class Row(BaseModel):
    userid:str
    sp_name: str
    update_time: str
    sp_no:str
    link_url: str
    xs_name: str
    applyer:str
    sp_status: str
    reject_reason: str
    dxl_number: str
    merchant_name: str
    purchase_price: str
    payment_date: str
    payment_method: str
    is_direct_delivery: str
    tracking_number:str
    needs_maintenance: str
    maintenance_person: str
    shipping_fee:str
    maintenance_content:str
    maintenance_price: str
    is_settled: str
    sx_jz_date:str
    settlement_date:str
    is_shipped:str
@app.post("/updateTableData")
async def update_table_data(row: Row):
    con = get_db_connection()
    cur = con.cursor()

    item_data = {
        "sp_name": row.sp_name,
        "update_time": row.update_time,
        "sp_no": row.sp_no,
        "link_url": row.link_url,
        "xs_name": row.xs_name,
        "applyer": row.applyer,
        "sp_status": row.sp_status,
        "reject_reason": row.reject_reason,
        "dxl_number": row.dxl_number,
        "merchant_name": row.merchant_name,
        "purchase_price": row.purchase_price,
        "payment_date": row.payment_date,
        "payment_method": row.payment_method,
        "is_direct_delivery": row.is_direct_delivery,
        "tracking_number": row.tracking_number,
        "needs_maintenance": row.needs_maintenance,
        "maintenance_person": row.maintenance_person,
        "shipping_fee": row.shipping_fee,
        "maintenance_content": row.maintenance_content,
        "maintenance_price": row.maintenance_price,
        "is_settled": row.is_settled,
        "sx_jz_date": row.sx_jz_date,
        "settlement_date": row.settlement_date,
        "is_shipped": row.is_shipped
    }

    # 直接更新
    cur.execute(
        "UPDATE XFZTABLEDATA SET OBJ_INFO = ? WHERE orderID = ?",
        (json.dumps(item_data), row.sp_no)
    )

    con.commit()
    con.close()

    return {
        "code": 200,
        "message": "保存成功"
    }

""" 根据图片ID数组获取图片 """
@app.get("/getPicture/")
async def getPicture(media_ids: List[str] = Query(alias="media_ids[]")):

    clear_static_folder(desktop_path)
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

""" 查询 Token 信息（通过 user_id）"""
async def get_token(user_id: str, token: str):
    con = get_db_connection()
    cur = con.cursor()

    cur.execute("SELECT token, create_time FROM xfztoken WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if not row:
        con.close()
        return True

    db_token, create_time = row

    # 判断是否超过8小时
    is_expired = create_time < datetime.now() - timedelta(hours=8)

    if db_token != token or is_expired:
        # 删除 token 记录
        cur.execute("DELETE FROM xfztoken WHERE user_id = ?", (user_id,))
        con.commit()
        con.close()
        return True
    else:
        con.close()
        return False

""" 管理员登录（针对 xfzadmin 表）"""
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

""" 普通用户登录 """
@app.post("/user/login")
async def user_login(data: LoginData):
    username = data.username
    password = data.password

    con = get_db_connection()
    cur = con.cursor()

    # 查询 xfzadmin 用户
    cur.execute("SELECT ID, PASSWORD,ROLE FROM XFZUSERS WHERE USERNAME = ?", (username,))
    row = cur.fetchone()

    if not row:
        con.close()
        raise True

    user_id, db_password,role = row
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

    # 编码成 Base64
    encoded_bytes = base64.b64encode(role.encode('utf-8'))
    role_encoded_str = encoded_bytes.decode('utf-8')

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "user_id": user_id,
            "user_name": username,
            "role": role_encoded_str,
            "token": token_str
        }
    }

""" 管理员 添加用户 """
class UserCreate(BaseModel):
    username: str
    password: str
    role:str
@app.post("/admin/add_user")
async def add_user(data: UserCreate):

    username = data.username
    password = data.password
    role = data.role

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
        INSERT INTO xfzusers (id, username, password,role, account_permission, column_permission)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        password,
        role,
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

""" 管理员 添加角色 """
class RoleCreate(BaseModel):
    role_name:str
@app.post("/admin/add_role")
async def add_role(data: RoleCreate):

    role_id = uuid.uuid4().hex
    role_name = data.role_name

    column_permission = {
        "销售类型": False,
        "填写日期": False,
        "订单编号": False,
        "超链接": False,
        "销售人": False,
        "审批人": False,
        "审批状态": False,
        "驳回原因": False,
        "段小狸编码": False,
        "商家名称": False,
        "采购价格": False,
        "付款日期": False,
        "支付方式": False,
        "是否直接发货": False,
        "快递单号": False,
        "是否需要养护": False,
        "养护人": False,
        "快递费": False,
        "养护内容": False,
        "养护价格": False,
        "是否结算": False,
        "结算日期": False,
        "是否发货": False,
        "操作": False,
        "上架商品图片": False,
        "销售订单截图": False,
        "运输面单截图": False
    }

    con = get_db_connection()
    cur = con.cursor()

    # 检查用户名是否已存在
    cur.execute("SELECT 1 FROM xfzrole WHERE role_name = ?", (role_name,))
    if cur.fetchone():
        con.close()
        raise HTTPException(status_code=400, detail="角色已存在")

    # 插入新用户
    cur.execute("""
        INSERT INTO xfzrole (role_id,role_name,column_permission)
        VALUES (?,?,?)
    """, (
        role_id,
        role_name,
        json.dumps(column_permission)
    ))

    con.commit()
    con.close()

    return {
        "code": 200,
        "message": "用户添加成功",
        "data": {
            "role_name": role_name
        }
    }

""" 管理员 查询全部用户 """
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
                "role": row[3],
                "account_permission": json.loads(row[4].replace("false", "false").replace("true", "true")),
                # 保险起见处理布尔大小写
                "column_permission": json.loads(row[5].replace("false", "false").replace("true", "true"))
            })

        return {
            "code": 200,
            "message": "查询成功",
            "data": users
        }

""" 管理员 查询全部角色 """
class UserGet(BaseModel):
    user_id: str
    token: str
@app.post("/admin/get_role")
async def get_role(data: UserGet):

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
        cur.execute("SELECT * FROM xfzrole")
        row = cur.fetchall()

        roles = []
        for row in row:
            roles.append({
                "role_id": row[0],
                "role_name": row[1],
                # 保险起见处理布尔大小写
                "column_permission": json.loads(row[2].replace("false", "false").replace("true", "true"))
            })

        return {
            "code": 200,
            "message": "查询成功",
            "data": roles
        }

""" 用户根据 ID 查询自己的表格的 列 权限信息 """
@app.post("/get_role_user_id")
async def get_role_user_id(data: UserGet):
    # 校验 token
    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }

    con = get_db_connection()
    cur = con.cursor()

    # 第一步：从 xfzusers 表获取 role 字段
    cur.execute("SELECT role FROM xfzusers WHERE id = ?", (data.user_id,))
    user_row = cur.fetchone()

    if not user_row or not user_row[0]:
        con.close()
        return {
            "code": 404,
            "message": "未找到用户角色信息",
            "data": []
        }

    role_name = user_row[0]  # 用户对应的角色

    # 第二步：查询该角色在 xfzrole 表中的权限
    cur.execute("SELECT role_id, role_name, column_permission FROM xfzrole WHERE role_name = ?", (role_name,))
    role_row = cur.fetchone()

    con.close()

    if not role_row:
        return {
            "code": 404,
            "message": f"未找到角色: {role_name} 的权限信息",
            "data": []
        }

    # 解析 column_permission JSON
    try:
        column_permission = json.loads(role_row[2])
    except Exception as e:
        return {
            "code": 500,
            "message": f"权限字段解析失败: {str(e)}",
            "data": []
        }

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "role_id": role_row[0],
            "role_name": role_row[1],
            "column_permission": column_permission
        }
    }

""" 删除用户 """
class Userdel(BaseModel):
    user_id: str
    token: str
    deluser_id:str
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

""" 管理员 修改用户信息加权限 """
class GetPERMISSION(BaseModel):
    user_id: str
    token: str
    UPuserid:str
    USERNAME:str
    PASSWORD:str
    ROLE: str
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
                    a.ROLE = ?,
                    a.ACCOUNT_PERMISSION = ?,
                    a.COLUMN_PERMISSION = ?
                WHERE
                    a.ID = ?

        """, (getPERMISSION.USERNAME,getPERMISSION.PASSWORD,getPERMISSION.ROLE,getPERMISSION.ACCOUNT_PERMISSION,getPERMISSION.COLUMN_PERMISSION,getPERMISSION.UPuserid))

        con.commit()

        con.close()

        return {
            "code": 200,
            "message": "修改成功",
            "data": True
        }


""" 管理员 修改用户信息加权限 """
class GetPERMISSION_Role(BaseModel):
    user_id: str
    token: str
    role_id: str
    role_name:str
    COLUMN_PERMISSION:str
@app.post("/admin/getRoleUP")
async def getRoleUP(GetPERMISSION_Role:GetPERMISSION_Role):

    if await get_token(GetPERMISSION_Role.user_id, GetPERMISSION_Role.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
           UPDATE XFZROLE a
                SET
                    a.role_name = ?,
                    a.COLUMN_PERMISSION = ?
                WHERE
                    a.role_id = ?

        """, (GetPERMISSION_Role.role_name,GetPERMISSION_Role.COLUMN_PERMISSION,GetPERMISSION_Role.role_id))

        con.commit()

        con.close()

        return {
            "code": 200,
            "message": "修改成功",
            "data": True
        }


""" 管理员 修改用户信息加权限 """
class ApprovalData(BaseModel):
    sp_no: str
    user_id: str
    token: str

@app.post("/ApprovalData")
async def App_roval_Data(data:ApprovalData):

    if await get_token(data.user_id, data.token):
        return {
            "code": 400,
            "message": "身份验证已过期",
            "data": []
        }
    else:

        url2 = f'https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={app.state.access_token}'
        item = requests.post(url2, json={"sp_no": data.sp_no}).json()

        time.sleep(0.2)

        # 获取映射 userid to username
        userid_to_name = await get_userid_to_name(app.state.access_token)

        # 替换人名
        item['info']['applyer']['userid'] = userid_to_name[1].get(item['info']['applyer']['userid'],item['info']['applyer']['userid'])

        """========================================================================================================================="""
        """========================================================================================================================="""
        """========================================================================================================================="""

        return {
            "code": 200,
            "message": "查询详情",
            "data": item
        }




""" 消息推送 """
async def approval_check():
    print(f"[{datetime.now()}] 执行审批检查")

    # 更新token
    app.state.access_token = await get_weChat_access_token()

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
                sp_type = ""
                sp_name = ""

                for content in item['info']['apply_data']['contents']:
                    for t in content.get("title", []):
                        text = t.get("text", "")
                        if text == "销售日期":
                            Date0 = content["value"]['date']['s_timestamp']
                        elif text == "销售类型":
                            sp_type = content['value']['selector']['options'][0]['value'][0]['text']
                        elif text == "销售截至日期":
                            Date1 = content["value"]['date']['s_timestamp']
                        elif text == "商品名称":
                            sp_name = content["value"]['text']

                    if Date0 and Date1 and sp_type and sp_name:
                        break

                if not Date0 or not Date1:
                    continue

                now_ts = int(time.time())
                diff_hours = (now_ts - int(Date0)) / 3600

                if diff_hours >= 72:
                    for sub_node_li in node['sub_node_list']:
                        if sub_node_li['sp_yj'] == 1:
                            content = (
                                f"订单号：{item['info']['sp_no']}\n"
                                f"发起人：{await get_name(token, item['info']['applyer']['userid'])}\n"
                                f"审批人：{await get_name(token, sub_node_li['userid'])}\n"
                                f"销售类型：{sp_type}\n"
                                f"商品名称：{sp_name}\n"
                                f"销售日期：{datetime.fromtimestamp(int(Date0)).strftime('%Y-%m-%d')}\n"
                                f"销售截止日期：{datetime.fromtimestamp(int(Date1)).strftime('%Y-%m-%d')}\n"
                                f"状态：审批已超时,需紧急处理"
                            )

                            await send_approval_alert(sub_node_li['userid'], token, content)

                            time.sleep(1)

                elif diff_hours >= 48:
                    for sub_node_li in node['sub_node_list']:
                        if sub_node_li['sp_yj'] == 1:
                            content = (
                                f"订单号：{item['info']['sp_no']}\n"
                                f"发起人：{await get_name(token, item['info']['applyer']['userid'])}\n"
                                f"审批人：{await get_name(token, sub_node_li['userid'])}\n"
                                f"销售类型：{sp_type}\n"
                                f"商品名称：{sp_name}\n"
                                f"销售日期：{datetime.fromtimestamp(int(Date0)).strftime('%Y-%m-%d')}\n"
                                f"销售截止日期：{datetime.fromtimestamp(int(Date1)).strftime('%Y-%m-%d')}\n"
                                f"状态：审批即将超时,请处理"
                            )

                            await send_approval_alert(sub_node_li['userid'], token, content)

                            time.sleep(1)

""" 消息推送 每到双数 整点 发送消息 """
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

# 测试 方法 时间 每分钟发一个
# async def wait_until_next_2_hour_mark():
#     now = datetime.now()
#     next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
#     wait_seconds = (next_run - now).total_seconds()
#     print(f"等待 {wait_seconds} 秒，到下一分钟整点: {next_run}")
#     await asyncio.sleep(wait_seconds)

""" 消息推送 定时循环 """
async def approval_check_loop():
    while True:
        await wait_until_next_2_hour_mark()
        await approval_check()

""" 消息推送 项目启动后再启动 """
@app.on_event("startup")
async def startup_event():
    app.state.access_token = await get_weChat_access_token()
    asyncio.create_task(approval_check_loop())





if __name__ == "__main__":

    uvicorn.run(app, host="127.0.0.1", port=8080, reload=False)


