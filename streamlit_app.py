#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股涨停板数据可视化 - Streamlit版
"""

import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

st.set_page_config(page_title="A股涨停板", page_icon="📈")

st.title("📈 A股涨停板数据")

# 备用数据
SAMPLE_DATA = [
    {"code": "301680.SZ", "name": "CPOE", "close": 126.71, "pct_change": 118.47, "volume": 129529},
    {"code": "688176.SH", "name": "亚虹医药", "close": 16.78, "pct_change": 20.03, "volume": 610776},
    {"code": "301218.SZ", "name": "开特股份", "close": 38.51, "pct_change": 20.01, "volume": 118486},
    {"code": "300323.SZ", "name": "华灿光电", "close": 11.94, "pct_change": 16.49, "volume": 3492782},
    {"code": "688248.SH", "name": "南网科技", "close": 58.07, "pct_change": 11.50, "volume": 153555},
    {"code": "000516.SZ", "name": "国际医学", "close": 5.01, "pct_change": 10.11, "volume": 673856},
    {"code": "002506.SZ", "name": "协鑫集成", "close": 5.56, "pct_change": 10.10, "volume": 10919285},
    {"code": "600406.SH", "name": "国电南瑞", "close": 29.60, "pct_change": 3.18, "volume": 5000000},
]

# 获取数据函数
@st.cache_data(ttl=3600)
def get_limit_up_stocks():
    urls = [
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f2,f3,f4,f12,f13,f14',
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f2,f3,f4,f12,f13,f14',
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=2000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f2,f3,f4,f12,f13,f14',
    ]
    
    all_stocks = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            diff = data.get('data', {}).get('diff', [])
            all_stocks.extend(diff)
            if all_stocks:
                break
        except:
            continue
    
    if not all_stocks:
        return None
    
    limit_up = []
    for d in all_stocks:
        pct = d.get('f3', 0)
        if pct >= 9.9:
            limit_up.append({
                'code': d.get('f12', ''),
                'name': d.get('f14', ''),
                'close': d.get('f2', 0),
                'pct_change': pct,
                'volume': d.get('f4', 0),
            })
    
    return pd.DataFrame(limit_up) if limit_up else None

# 侧边栏
st.sidebar.header("筛选")
show_st = st.sidebar.checkbox("显示ST股", value=False)

# 获取数据
df = get_limit_up_stocks()

if df is None or len(df) == 0:
    st.warning("API暂时无法获取数据，显示示例数据")
    df = pd.DataFrame(SAMPLE_DATA)

# 过滤ST
if not show_st:
    df = df[~df['name'].astype(str).str.contains('ST|退', na=False)]

df = df.sort_values('pct_change', ascending=False)

st.metric("涨停数量", len(df))

tab1, tab2, tab3 = st.tabs(["列表", "图表", "热门"])

with tab1:
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("涨幅分布")
    st.bar_chart(df['pct_change'].head(20))
    
    st.subheader("成交额TOP10")
    top10 = df.nlargest(10, 'volume')
    st.bar_chart(top10.set_index('name')['volume'])

with tab3:
    st.subheader("今日涨停")
    for i, row in df.head(10).iterrows():
        st.write(f"**{row['name']}** ({row['code']}) - {row['pct_change']:+.2f}%")

st.caption(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
