import json
from pathlib import Path
import fdb

# # # 插入数据
# def insert_json_to_firebird_one(order_id, obj,user: str = "SYSDBA", password: str = "xiaofeizhu"):
#     try:
#         db_file = r"C:\Firebird_DB\my_db.fdb"
#         dsn = f"localhost:{db_file}"
#
#         con = fdb.connect(
#             dsn=dsn,
#             user=user,
#             password=password,
#             charset='UTF8'
#         )
#         cur = con.cursor()
#
#         # 检查是否已存在
#         cur.execute("SELECT 1 FROM XFZTABLEDATA WHERE ORDERID = ?", (order_id,))
#         if cur.fetchone():
#             print(f"⏩ 跳过已存在的 ORDERID：{order_id}")
#         else:
#
#             blob_json = json.dumps(obj)
#
#             cur.execute(
#                 "INSERT INTO XFZTABLEDATA (ORDERID, OBJ_INFO) VALUES (?, ?)",
#                 (order_id, blob_json)
#             )
#             print(f"✅ 插入新记录：{order_id}")
#
#             con.commit()
#
#     except Exception as e:
#         print(f"❌ 发生错误：{e}")
#     finally:
#         if 'cur' in locals():
#             cur.close()
#         if 'con' in locals():
#             con.close()
#
#
# # 定义 txtFiles 目录路径（相对于当前脚本运行位置）
# json_dir = Path('restore/refactoring_the_structure/txtFiles')
#
# # 遍历 txtFiles 目录下所有 .txt 文件
# for txt_file in json_dir.glob('*.txt'):
#
#     with open(txt_file, 'r', encoding='utf-8') as f:
#         content = json.loads(f.read())
#
#         for order_id, obj in content.items():
#             insert_json_to_firebird_one(order_id, obj)