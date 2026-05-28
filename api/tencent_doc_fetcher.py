"""
腾讯文档数据获取模块
支持从腾讯文档公开链接获取表格数据
"""

import requests
import re
import json
import pandas as pd
from typing import Optional, Tuple


class TencentDocFetcher:
    """腾讯文档数据获取器"""

    def __init__(self, doc_url: str, cookie: str = ""):
        """
        初始化

        Args:
            doc_url: 腾讯文档分享链接
            cookie: 可选的cookie字符串，用于获取需要登录的文档
        """
        self.doc_url = doc_url
        self.cookie = cookie
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if cookie:
            self.headers['Cookie'] = cookie

    def extract_doc_id(self) -> Optional[str]:
        """从URL中提取文档ID"""
        match = re.search(r'/sheet/([A-Za-z0-9]+)', self.doc_url)
        if match:
            return match.group(1)
        return None

    def fetch_data(self) -> Tuple[Optional[pd.DataFrame], str]:
        """
        获取文档数据

        Returns:
            (DataFrame, error_message)
        """
        try:
            doc_id = self.extract_doc_id()
            if not doc_id:
                return None, "无法从URL中提取文档ID"

            # 获取文档页面
            response = requests.get(self.doc_url, headers=self.headers, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                return None, f"请求失败，状态码: {response.status_code}"

            html_content = response.text

            # 尝试从页面中提取数据
            # 腾讯文档的数据通常嵌入在 JavaScript 变量中
            data = self._extract_data_from_html(html_content)

            if data is not None:
                return data, ""

            # 如果无法直接提取，尝试使用导出API
            return self._try_export_api(doc_id)

        except requests.Timeout:
            return None, "请求超时，请检查网络连接"
        except Exception as e:
            return None, f"获取数据时发生错误: {str(e)}"

    def _extract_data_from_html(self, html: str) -> Optional[pd.DataFrame]:
        """从HTML中提取表格数据"""
        try:
            # 尝试匹配腾讯文档的数据格式
            # 数据通常在 window.SHEET_DATA 或类似变量中

            # 方法1: 查找 sheetData 变量
            pattern = r'window\.(?:INITIAL_STATE|sheetData|SHEET_DATA)\s*=\s*({.*?});'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                data_json = match.group(1)
                data = json.loads(data_json)
                return self._parse_sheet_data(data)

            # 方法2: 查找 cells 数据
            pattern = r'"cells"\s*:\s*(\[.*?\])'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                cells_json = match.group(1)
                cells = json.loads(cells_json)
                return self._parse_cells_data(cells)

            return None

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"解析HTML数据失败: {e}")
            return None

    def _parse_sheet_data(self, data: dict) -> Optional[pd.DataFrame]:
        """解析sheet数据格式"""
        try:
            # 提取单元格数据
            if 'sheet' in data and 'cells' in data['sheet']:
                cells = data['sheet']['cells']
            elif 'cells' in data:
                cells = data['cells']
            else:
                return None

            return self._parse_cells_data(cells)

        except Exception as e:
            print(f"解析sheet数据失败: {e}")
            return None

    def _parse_cells_data(self, cells: list) -> Optional[pd.DataFrame]:
        """解析单元格数据"""
        try:
            if not cells:
                return None

            # 找出最大行和列
            max_row = 0
            max_col = 0

            for cell in cells:
                if isinstance(cell, dict):
                    row = cell.get('row', 0)
                    col = cell.get('col', 0)
                    max_row = max(max_row, row)
                    max_col = max(max_col, col)
                elif isinstance(cell, list) and len(cell) >= 2:
                    row, col = cell[0], cell[1]
                    max_row = max(max_row, row)
                    max_col = max(max_col, col)

            if max_row == 0 or max_col == 0:
                return None

            # 创建表格
            table = [[''] * (max_col + 1) for _ in range(max_row + 1)]

            for cell in cells:
                if isinstance(cell, dict):
                    row = cell.get('row', 0)
                    col = cell.get('col', 0)
                    value = cell.get('value', '') or cell.get('text', '')
                    table[row][col] = str(value)
                elif isinstance(cell, list) and len(cell) >= 3:
                    row, col, value = cell[0], cell[1], cell[2]
                    table[row][col] = str(value)

            # 转换为DataFrame
            if len(table) > 1:
                df = pd.DataFrame(table[1:], columns=table[0])
                return df

            return None

        except Exception as e:
            print(f"解析单元格数据失败: {e}")
            return None

    def _try_export_api(self, doc_id: str) -> Tuple[Optional[pd.DataFrame], str]:
        """尝试使用导出API"""
        try:
            # 腾讯文档导出接口（需要登录）
            export_url = f"https://docs.qq.com/export/api/sheet/{doc_id}"

            response = requests.get(
                export_url,
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )

            if response.status_code == 200:
                # 尝试解析返回的数据
                content_type = response.headers.get('Content-Type', '')

                if 'json' in content_type:
                    data = response.json()
                    if 'data' in data:
                        return self._parse_sheet_data(data['data']), ""

                if 'spreadsheet' in content_type or 'excel' in content_type:
                    # 如果返回的是Excel文件
                    import io
                    df = pd.read_excel(io.BytesIO(response.content))
                    return df, ""

            return None, "无法通过API获取数据，可能需要登录权限"

        except Exception as e:
            return None, f"API请求失败: {str(e)}"


def fetch_tencent_doc(doc_url: str, cookie: str = "") -> Tuple[Optional[pd.DataFrame], str]:
    """
    便捷函数：获取腾讯文档数据

    Args:
        doc_url: 腾讯文档分享链接
        cookie: 可选的cookie字符串

    Returns:
        (DataFrame, error_message)
    """
    fetcher = TencentDocFetcher(doc_url, cookie)
    return fetcher.fetch_data()


if __name__ == "__main__":
    # 测试代码
    test_url = "https://docs.qq.com/sheet/DTmh6R1RpZW9RbXZq?tab=BB08J2"
    df, error = fetch_tencent_doc(test_url)

    if df is not None:
        print("成功获取数据！")
        print(f"共 {len(df)} 行数据")
        print("\n列名:")
        print(df.columns.tolist())
    else:
        print(f"获取数据失败: {error}")
