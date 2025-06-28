import json
import os
import requests
from datetime import datetime

""" 获取企业微信令牌(access_token) """
async def get_weChat_access_token():

    # 企业ID和应用密钥
    corpid = "wwf9d174d0050cf1bd"
    corpsecret = "v5Eb4813bIclbeQOoFTqnamIa4NiulXPCAu4IEtsI0A"

    # 请求 URL
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"

    # 发起请求
    response = requests.get(url)
    result = response.json()

    # 打印 access_token
    if result.get("errcode") == 0:

        return result["access_token"]

    else:

        return "获取失败：", result

""" 发送预警消息 """
async def send_approval_alert(touser,access_token,content):

    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    data = {
        "touser": str(touser),
        "toparty": "@all",
        "totag": "@all",
        "msgtype": "text",
        "agentid": 1000008,
        "text" : {
            "content" : content
        },
        "safe": 0,
        "enable_id_trans": 0,
        "enable_duplicate_check": 0,
        "duplicate_check_interval": 1800
    }

    response = requests.post(url, json=data).json()


    if response['errmsg'] == "ok":
        print(f"发送消息至 {touser} 成功 日期：{datetime.now()}")

""" 把 userid 转换成真实姓名 """
async def get_name(access_token, username):
    url = f'https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={access_token}&userid={username}'
    response = requests.get(url).json()
    return response["name"]

""" 把 userid 和 真实姓名做成映射 """
async def get_userid_to_name(access_token):
    userid_to_name = {}
    name_to_userid = {}

    for i in range(1, 10):
        url = f'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token={access_token}&department_id={i}'
        response = requests.get(url).json()
        userlist = response.get('userlist', [])

        for user in userlist:
            userid_to_name[user['userid']] = user['name']
            name_to_userid[user['name']] = user['userid']

    return [name_to_userid, userid_to_name]

""" 删除所有下载的图片 """
def clear_static_folder(desktop_path):
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


""" 查询订单号是否存在 """
def order_exists(cur, orderID):
    cur.execute("SELECT FIRST 1 1 FROM XFZTABLEDATA WHERE orderID = ?", (str(orderID),))
    return cur.fetchone() is not None

# 插入数据
def insert_json_to_firebird(cur, con,order_id, obj):
    try:
        # 检查是否已存在
        cur.execute("SELECT 1 FROM XFZTABLEDATA WHERE ORDERID = ?", (order_id,))
        if cur.fetchone():
            print(f"⏩ 跳过已存在的 ORDERID：{order_id}")
        else:

            blob_json = json.dumps(obj)

            cur.execute(
                "INSERT INTO XFZTABLEDATA (ORDERID, OBJ_INFO) VALUES (?, ?)",
                (order_id, blob_json)
            )
            con.commit()
            print(f"✅ 插入新记录：{order_id}")

    except Exception as e:
        print(f"❌ 发生错误：{e}")

