from fastapi import FastAPI
from weChat.tool import get_weChat_access_token

"""
    引用 FastAPI 函数
"""
app = FastAPI()

"""
    项目启动时自动引用
"""
@app.on_event("startup")
async def startup_event():
    token = await get_weChat_access_token()
    app.state.access_token = token

@app.get("/")
async def root():
    return {"令牌": app.state.access_token}
