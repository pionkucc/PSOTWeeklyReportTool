"""
主API接口
返回前端报告页面和数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, render_template_string, send_from_directory
import json
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any

from data_processor import get_all_chart_data
from tencent_doc_fetcher import fetch_tencent_doc

app = Flask(__name__, static_folder='../templates')

# 配置
DOC_URL = "https://docs.qq.com/sheet/DTmh6R1RpZW9RbXZq?tab=BB08J2"
DATA_CACHE_FILE = "/tmp/report_data.json"
COOKIE = os.environ.get("TENCENT_DOC_COOKIE", "")

# 本地Excel文件路径（备选方案）
LOCAL_EXCEL_PATH = None  # 部署时可以设置

# 颜色配置
COLORS = {
    'pastel': ['#A8D8EA', '#AA96DA', '#FCBAD3', '#FFFFD2', '#C4E1C1', '#F9D5A7', '#B8E0D2', '#D6EADF'],
    'fresh': ['#7FB3D5', '#76D7C4', '#F7DC6F', '#F0B27A', '#E59866', '#AF7AC5', '#85C1E9', '#82E0AA'],
    'status': {'New': '#F7DC6F', 'Closed': '#82E0AA', 'ReOpen': '#F0B27A', 'Pending': '#85C1E9', 'Fixed': '#76D7C4'},
    'status_soft': {'Closed': '#B8E0D2', 'Fixed': '#D6EADF', 'New': '#A8D8EA', 'Pending': '#AA96DA', 'ReOpen': '#F9D5A7'},
    'priority': {'优先': '#E57373', '高': '#FFB74D', '中': '#64B5F6', '低': '#81C784'},
    'severity': {'严重': '#E57373', '一般': '#FFB74D', '轻微': '#64B5F6', '建议': '#81C784'},
}


def load_cached_data() -> Optional[Dict[str, Any]]:
    """加载缓存数据"""
    try:
        if os.path.exists(DATA_CACHE_FILE):
            with open(DATA_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载缓存失败: {e}")
    return None


def save_cached_data(data: Dict[str, Any]):
    """保存缓存数据"""
    try:
        with open(DATA_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存缓存失败: {e}")


def fetch_and_process_data() -> Dict[str, Any]:
    """获取并处理数据"""
    # 方案1: 尝试从腾讯文档获取
    if COOKIE:
        df, error = fetch_tencent_doc(DOC_URL, COOKIE)
        if df is not None:
            return _process_dataframe(df)

    # 方案2: 尝试使用本地缓存
    cached = load_cached_data()
    if cached:
        return cached

    # 方案3: 返回演示数据
    return _get_demo_data()


def _process_dataframe(df) -> Dict[str, Any]:
    """处理DataFrame并返回结果"""
    chart_data = get_all_chart_data(df)

    result = {
        'success': True,
        'colors': COLORS,
        'data': chart_data,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    save_cached_data(result)
    return result


def _get_demo_data() -> Dict[str, Any]:
    """返回演示数据（用于首次访问）"""
    return {
        'success': True,
        'colors': COLORS,
        'data': {
            'metrics': {
                'total': 0,
                'new_count': 0,
                'closed_count': 0,
                'fixed_count': 0,
                'legacy_count': 0,
                'close_rate': 0,
                'avg_fix_time': 0
            },
            'handler_stats': {'handlers': [], 'status_data': {}, 'totals': [], 'avg_fix_time': []},
            'trend': {'dates': [], 'new_data': [], 'closed_data': [], 'legacy_data': []},
            'status_dist': {'labels': [], 'values': []},
            'task_dist': {'labels': [], 'values': []},
            'rework_dist': {'labels': [], 'values': []},
            'stage_dist': {'labels': [], 'values': []},
            'type_dist': {'labels': [], 'values': []},
            'cause_dist': {'labels': [], 'values': []},
            'priority_dist': {'labels': [], 'values': []},
            'severity_dist': {'labels': [], 'values': []},
            'intro_dist': {'labels': [], 'values': []},
            'raw_data': []
        },
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message': '请配置Cookie或上传数据以获取真实数据'
    }


@app.route('/')
def index():
    """返回报告页面"""
    # 读取HTML模板
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'index.html')

    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    else:
        return '''
        <html>
        <head><title>缺陷质量分析报告</title></head>
        <body>
            <h1>缺陷质量分析报告</h1>
            <p>模板文件未找到，请访问 <a href="/api/data">/api/data</a> 获取数据</p>
        </body>
        </html>
        '''


@app.route('/api/data')
def get_data():
    """获取报告数据API"""
    result = fetch_and_process_data()
    return jsonify(result)


@app.route('/api/status')
def get_status():
    """获取同步状态"""
    cached = load_cached_data()
    return jsonify({
        'has_cache': cached is not None,
        'last_update': cached.get('last_update') if cached else None
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    """上传Excel文件"""
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
        result = _process_dataframe(df)

        return jsonify({
            'success': True,
            'message': f'成功导入 {len(df)} 条数据',
            'last_update': result['last_update']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'文件处理失败: {str(e)}'})


# Vercel需要的handler
def handler(request):
    """Vercel serverless handler"""
    return app(request.environ, lambda status, headers: None)


if __name__ == '__main__':
    # 本地测试
    print("启动本地服务器...")
    print("访问 http://localhost:5000 查看报告")

    # 测试数据获取
    print("\n测试数据获取...")
    result = fetch_and_process_data()
    if result.get('success'):
        print(f"成功! 共 {result['data']['metrics']['total']} 条数据")
        print(f"更新时间: {result['last_update']}")
    else:
        print(f"失败: {result.get('error')}")

    app.run(debug=True, port=5000)
