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




