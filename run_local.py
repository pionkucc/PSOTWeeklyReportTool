"""
本地开发服务器
用于测试Web应用

运行方式:
    python run_local.py

访问地址:
    http://localhost:5000
"""

import os
import sys

# 添加api目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from api.index import app

if __name__ == '__main__':
    print("=" * 50)
    print("缺陷质量分析报告 - 本地开发服务器")
    print("=" * 50)
    print("\n访问地址: http://localhost:5000")
    print("同步接口: http://localhost:5000/sync")
    print("\n按 Ctrl+C 停止服务器\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
