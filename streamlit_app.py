#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股涨停板数据可视化 - Streamlit版(升级)
"""

import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="A股涨停板", page_icon="📈", layout="wide")

# 样式
st.markdown("""
<style>
    .main { background-color: #0e1117 }
    h1 { color: #ff4b4b; text-align: center; }
    .stMetric { background-color: #262730; padding: 10px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📈 A股涨停板数据中心")

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
with st.sidebar:
    st.header("⚙️ 设置")
    show_st = st.checkbox("显示ST股", value=False)
    st.markdown("---")
    st.markdown("**📊 数据来源**")
    st.caption("东方财富API")

# 主内容
df = get_limit_up_stocks()

if df is None or len(df) == 0:
    st.warning("⚠️ API暂时无法获取数据，显示示例数据")
    df = pd.DataFrame(SAMPLE_DATA)

# 过滤ST
if not show_st:
    df = df[~df['name'].astype(str).str.contains('ST|退', na=False)]

df = df.sort_values('pct_change', ascending=False)

# 顶部统计
col1, col2, col3, col4 = st.columns(4)
col1.metric("🔥 涨停数量", len(df))
col2.metric("📈 最高涨幅", f"{df['pct_change'].max():.2f}%")
col3.metric("💰 总成交额", f"{df['volume'].sum()/10000:.0f}万")
col4.metric("⏰ 更新时间", datetime.now().strftime("%H:%M"))

# 标签页
tab1, tab2, tab3 = st.tabs(["📊 数据看板", "📈 图表分析", "🔥 热门个股"])

with tab1:
    st.dataframe(
        df[['code', 'name', 'close', 'pct_change', 'volume']].rename(columns={
            'code': '代码', 'name': '名称', 'close': '收盘价', 'pct_change': '涨跌幅%', 'volume': '成交量'
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            '涨跌幅%': st.column_config.NumberColumn(format="%.2f%%"),
            '收盘价': st.column_config.NumberColumn(format="¥%.2f"),
            '成交量': st.column_config.NumberColumn(format="%d"),
        }
    )

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 涨幅排行 TOP15")
        top15 = df.head(15)
        fig1 = px.bar(top15, x='name', y='pct_change', color='pct_change', color_continuous_scale='Reds', title="")
        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=400)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("💰 成交额排行 TOP15")
        top15_vol = df.nlargest(15, 'volume')
        fig2 = px.bar(top15_vol, x='name', y='volume', color='volume', color_continuous_scale='Blues', title="")
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=400)
        st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("📉 涨幅 vs 成交额")
    fig3 = px.scatter(df, x='volume', y='pct_change', size='close', color='pct_change', hover_name='name', color_continuous_scale='RdYlGn', title="")
    fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=400)
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    st.subheader("🏆 今日涨停明星")
    cols = st.columns(3)
    for i, (_, row) in enumerate(df.head(9).iterrows()):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; margin: 10px 0;">
                <h3 style="margin:0; color: white;">{row['name']}</h3>
                <p style="color: #ddd; margin: 5px 0;">{row['code']}</p>
                <h2 style="margin: 10px 0; color: #ffd700;">{row['pct_change']:+.2f}%</h2>
                <p style="color: #aaa;">¥{row['close']}</p>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.caption(f"⏰ 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据来源: 东方财富")
