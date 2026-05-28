"""
数据处理模块
负责数据预处理和统计分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    预处理数据
    """
    # 修复周期列类型转换
    if '缺陷修复周期(天)' in df.columns:
        df['缺陷修复周期(天)'] = pd.to_numeric(
            df['缺陷修复周期(天)'].replace('/', np.nan), errors='coerce'
        )

    if '缺陷关闭周期(天)' in df.columns:
        df['缺陷关闭周期(天)'] = pd.to_numeric(
            df['缺陷关闭周期(天)'].replace('/', np.nan), errors='coerce'
        )

    # 返工次数处理
    if '返工次数' in df.columns:
        df['返工次数'] = pd.to_numeric(df['返工次数'], errors='coerce').fillna(0).astype(int)

    return df


def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    计算质量指标概览
    """
    total = len(df)

    # 状态统计
    status_counts = df['缺陷状态'].value_counts().to_dict() if '缺陷状态' in df.columns else {}

    # 新增缺陷
    new_count = status_counts.get('New', 0)

    # 已关闭缺陷
    closed_count = status_counts.get('Closed', 0)

    # 已修复缺陷
    fixed_count = status_counts.get('Fixed', 0)

    # 遗留缺陷
    legacy_count = total - closed_count

    # 关闭率
    close_rate = round(closed_count / total * 100, 1) if total > 0 else 0

    # 平均修复周期
    avg_fix_time = 0
    if '缺陷修复周期(天)' in df.columns:
        avg_fix_time = round(df['缺陷修复周期(天)'].dropna().mean(), 2)

    return {
        'total': total,
        'new_count': new_count,
        'closed_count': closed_count,
        'fixed_count': fixed_count,
        'legacy_count': legacy_count,
        'close_rate': close_rate,
        'avg_fix_time': avg_fix_time,
        'status_counts': status_counts
    }


def get_handler_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    处理人员缺陷统计
    """
    if '处理人员' not in df.columns or '缺陷状态' not in df.columns:
        return {'handlers': [], 'data': {}}

    status_list = ['Closed', 'Fixed', 'New', 'Pending', 'ReOpen']

    handler_status = df.groupby(['处理人员', '缺陷状态']).size().unstack(fill_value=0)

    for status in status_list:
        if status not in handler_status.columns:
            handler_status[status] = 0

    handler_status = handler_status[status_list]
    handler_totals = handler_status.sum(axis=1)
    handler_status = handler_status.loc[handler_totals.sort_values(ascending=False).index]

    # 平均修复时间
    avg_fix_time = {}
    if '缺陷修复周期(天)' in df.columns:
        avg_fix_time = df.groupby('处理人员')['缺陷修复周期(天)'].mean().to_dict()

    handlers = handler_status.index.tolist()

    result = {
        'handlers': handlers,
        'status_data': {status: handler_status[status].tolist() for status in status_list},
        'totals': handler_status.sum(axis=1).tolist(),
        'avg_fix_time': [round(avg_fix_time.get(h, 0), 2) for h in handlers]
    }

    return result


def get_trend_data(df: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    缺陷趋势数据
    """
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
    except:
        start = pd.to_datetime('2026-05-18')
        end = pd.to_datetime('2026-05-22')

    date_range = pd.date_range(start=start, end=end, freq='D')
    all_dates = [d.strftime('%m-%d') for d in date_range]

    # 尝试找到时间列
    register_col = None
    close_col = None

    for col in df.columns:
        if '登记时间' in col and register_col is None:
            register_col = col
        if '关闭时间' in col and close_col is None:
            close_col = col

    if register_col is None:
        register_col = df.columns[11] if len(df.columns) > 11 else df.columns[0]

    if close_col is None:
        close_col = df.columns[13] if len(df.columns) > 13 else df.columns[0]

    df['_reg_date'] = pd.to_datetime(df[register_col], errors='coerce').dt.strftime('%m-%d')
    df['_close_date'] = pd.to_datetime(df[close_col], errors='coerce').dt.strftime('%m-%d')

    # 新增缺陷
    new_counts = df[df['缺陷状态'] == 'New'].groupby('_reg_date').size() if '缺陷状态' in df.columns else pd.Series()

    # 关闭缺陷
    closed_counts = df[df['缺陷状态'] == 'Closed'].groupby('_close_date').size() if '缺陷状态' in df.columns else pd.Series()

    # 遗留缺陷
    legacy_df = df[df['缺陷状态'].isin(['New', 'ReOpen', 'Pending', 'Fixed'])] if '缺陷状态' in df.columns else df
    legacy_counts = legacy_df.groupby('_reg_date').size()

    new_data = [int(new_counts.get(d, 0)) for d in all_dates]
    closed_data = [int(closed_counts.get(d, 0)) for d in all_dates]
    legacy_data = [int(legacy_counts.get(d, 0)) for d in all_dates]

    return {
        'dates': all_dates,
        'new_data': new_data,
        'closed_data': closed_data,
        'legacy_data': legacy_data
    }


def get_distribution_data(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    获取某列的分布数据
    """
    if column not in df.columns:
        return {'labels': [], 'values': []}

    counts = df[column].value_counts()
    return {
        'labels': counts.index.tolist(),
        'values': counts.values.tolist()
    }


def get_all_chart_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    获取所有图表所需的数据
    """
    df = preprocess_data(df)

    # 提取时间范围
    start_date = '2026-05-18'
    end_date = '2026-05-22'

    # 尝试从数据推断时间范围
    if '登记时间' in df.columns:
        dates = pd.to_datetime(df['登记时间'], errors='coerce').dropna()
        if len(dates) > 0:
            start_date = dates.min().strftime('%Y-%m-%d')
            end_date = dates.max().strftime('%Y-%m-%d')

    return {
        'metrics': calculate_metrics(df),
        'handler_stats': get_handler_stats(df),
        'trend': get_trend_data(df, start_date, end_date),
        'status_dist': get_distribution_data(df, '缺陷状态'),
        'task_dist': get_distribution_data(df, '关联任务项'),
        'rework_dist': get_distribution_data(df, '返工次数'),
        'stage_dist': get_distribution_data(df, '发现阶段'),
        'type_dist': get_distribution_data(df, '缺陷类型'),
        'cause_dist': get_distribution_data(df, '引入原因'),
        'priority_dist': get_distribution_data(df, '优先级'),
        'severity_dist': get_distribution_data(df, '严重程度'),
        'intro_dist': get_distribution_data(df, '引入阶段'),
        'raw_data': df.to_dict(orient='records')[:100]  # 明细数据，限制100条
    }
