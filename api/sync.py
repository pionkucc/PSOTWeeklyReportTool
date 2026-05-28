"""
数据同步接口
手动触发同步，支持Cookie配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request
import json
import pandas as pd
from datetime import datetime

from data_processor import get_all_chart_data
from tencent_doc_fetcher import fetch_tencent_doc

app = Flask(__name__)

DOC_URL = "https://docs.qq.com/sheet/DTmh6R1RpZW9RbXZq?tab=BB08J2"
DATA_CACHE_FILE = "/tmp/report_data.json"

COLORS = {
    'pastel': ['#A8D8EA', '#AA96DA', '#FCBAD3', '#FFFFD2', '#C4E1C1', '#F9D5A7', '#B8E0D2', '#D6EADF'],
    'fresh': ['#7FB3D5', '#76D7C4', '#F7DC6F', '#F0B27A', '#E59866', '#AF7AC5', '#85C1E9', '#82E0AA'],
    'status': {'New': '#F7DC6F', 'Closed': '#82E0AA', 'ReOpen': '#F0B27A', 'Pending': '#85C1E9', 'Fixed': '#76D7C4'},
    'status_soft': {'Closed': '#B8E0D2', 'Fixed': '#D6EADF', 'New': '#A8D8EA', 'Pending': '#AA96DA', 'ReOpen': '#F9D5A7'},
    'priority': {'优先': '#E57373', '高': '#FFB74D', '中': '#64B5F6', '低': '#81C784'},
    'severity': {'严重': '#E57373', '一般': '#FFB74D', '轻微': '#64B5F6', '建议': '#81C784'},
}


def save_cached_data(data):
    """保存缓存数据"""
    try:
        with open(DATA_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存缓存失败: {e}")


@app.route('/sync', methods=['GET', 'POST'])
def sync_data():
    """手动触发同步"""
    # 从环境变量或请求参数获取Cookie
    cookie = os.environ.get("TENCENT_DOC_COOKIE", "")

    if request.method == 'POST':
        data = request.get_json() or {}
        if 'cookie' in data:
            cookie = data['cookie']

    # 尝试从腾讯文档获取
    df, error = fetch_tencent_doc(DOC_URL, cookie)

    if df is None:
        return jsonify({
            'success': False,
            'error': error or '获取数据失败，请检查Cookie配置',
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'help': '请参考文档配置腾讯文档Cookie'
        })

    # 处理数据
    chart_data = get_all_chart_data(df)

    result = {
        'success': True,
        'colors': COLORS,
        'data': chart_data,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    save_cached_data(result)

    return jsonify(result)


@app.route('/upload', methods=['POST'])
def upload_data():
    """上传Excel文件同步数据"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'})

    try:
        df = pd.read_excel(file)

        if len(df) == 0:
            return jsonify({'success': False, 'error': '文件没有数据'})

        # 处理数据
        chart_data = get_all_chart_data(df)

        result = {
            'success': True,
            'colors': COLORS,
            'data': chart_data,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        save_cached_data(result)

        return jsonify({
            'success': True,
            'message': f'成功导入 {len(df)} 条数据',
            'last_update': result['last_update']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'文件处理失败: {str(e)}'})


def handler(request):
    """Vercel serverless handler"""
    return app(request.environ, lambda status, headers: None)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
