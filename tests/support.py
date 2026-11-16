"""pytest 测试辅助工具：构造上传工作簿、读取导出结果。"""
import io

from openpyxl import Workbook, load_workbook

HEADERS = ["姓名", "收藏", "手机", "电话", "邮箱", "微信", "QQ", "微博", "地址", "其他联系方式", "备注"]
LABEL_HEADERS = ["联系人行号", "方式类型", "同类型序号", "联系方式内容", "标签"]


def workbook_stream(rows, headers=None, labels=None):
    """生成一个内存中的 .xlsx 文件流；labels 为标签工作表的数据行。"""
    book = Workbook()
    sheet = book.active
    sheet.title = "通讯录"
    sheet.append(headers if headers is not None else HEADERS)
    for row in rows:
        sheet.append(row)
    if labels is not None:
        label_sheet = book.create_sheet("联系方式标签")
        label_sheet.append(LABEL_HEADERS)
        for row in labels:
            label_sheet.append(row)
    stream = io.BytesIO()
    book.save(stream)
    book.close()
    stream.seek(0)
    return stream


def upload(client, stream, filename="contacts.xlsx", mode=None, endpoint="/api/contacts/import"):
    data = {"file": (stream, filename)}
    if mode:
        data["mode"] = mode
    return client.post(endpoint, data=data, content_type="multipart/form-data")


def exported_workbook(client, query_string=None):
    response = client.get("/api/contacts/export", query_string=query_string or {})
    assert response.status_code == 200, response.get_data(as_text=True)
    return load_workbook(io.BytesIO(response.data))


def export_rows(client, query_string=None):
    """返回导出文件主表的数据行（不含表头）。"""
    book = exported_workbook(client, query_string)
    sheet = book["通讯录"]
    return [list(row) for row in sheet.iter_rows(min_row=2, values_only=True)]


def contact_rows(client, **params):
    response = client.get("/api/contacts", query_string=params)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()
