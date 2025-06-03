from datetime import datetime

import requests

"""
    获取企业微信令牌(access_token)
"""
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


"""
    发送预警消息
"""
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

"""
    把 userid 转换成真实姓名
"""
async def get_name(access_token, username):
    url = f'https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={access_token}&userid={username}'
    response = requests.get(url).json()
    return response["name"]

"""
    把 userid 和 真实姓名做成映射
"""
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