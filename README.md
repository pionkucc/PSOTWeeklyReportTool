# 缺陷质量分析报告 - Web应用

在线访问的缺陷质量分析报告系统，支持上传Excel数据自动生成报告。

## 功能特点

- 📊 交互式图表展示
- 📤 支持上传Excel文件同步数据
- 🔄 页面手动同步按钮
- 📋 图表/表格视图切换
- 🔍 放大查看详情

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt
python run_local.py
```

访问 http://localhost:5000

### 部署到Vercel

1. Fork 或 Clone 本仓库
2. 登录 [Vercel](https://vercel.com)
3. 导入本项目
4. 点击 Deploy

## 数据同步方式

### 方式1：上传Excel文件
点击页面上的「📤 上传Excel」按钮，选择本地Excel文件即可。

### 方式2：配置腾讯文档Cookie（可选）
如需自动从腾讯文档同步，需配置环境变量：
- 名称：`TENCENT_DOC_COOKIE`
- 值：从浏览器开发者工具获取的Cookie

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 报告页面 |
| `/api/data` | GET | 获取报告数据 |
| `/sync` | GET | 手动同步 |
| `/upload` | POST | 上传Excel |

## 项目结构

```
├── api/
│   ├── index.py              # 主API
│   ├── sync.py               # 同步接口
│   ├── data_processor.py     # 数据处理
│   └── tencent_doc_fetcher.py
├── templates/
│   └── index.html            # 前端页面
├── requirements.txt
├── vercel.json
└── run_local.py
```

## License

MIT