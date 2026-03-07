import streamlit as st
import pandas as pd
import urllib.request
import json
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title='A股涨停板监控',
    page_icon='chart_with_upwards_trend',
)

@st.cache_data(ttl='1h')
def get_limit_up_stocks():
    urls = [
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f1,f2,f3,f4,f12,f13,f14',
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f1,f2,f3,f4,f12,f13,f14',
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f12,f13,f14',
    ]
    all_stocks = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read().decode('utf-8'))
            diff = data.get('data', {}).get('diff', [])
            all_stocks.extend(diff)
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    limit_up = []
    for d in all_stocks:
        pct = d.get('f3', 0)
        if pct >= 9.9:
            code = d.get('f12', '')
            name = d.get('f14', '')
            close = d.get('f2', 0)
            if code.startswith('300') or code.startswith('301'):
                market = '创业板'
            elif code.startswith('688'):
                market = '科创板'
            elif code.startswith('600') or code.startswith('601') or code.startswith('603'):
                market = '沪市主板'
            elif code.startswith('000') or code.startswith('002'):
                market = '深市主板/中小板'
            else:
                market = '其他'
            limit_up.append({'代码': code, '名称': name, '收盘价': close, '涨幅(%)': round(pct, 2), '市场': market})
    return pd.DataFrame(limit_up)

def load_history_data():
    """Load historical limit up data"""
    history_files = {
        '2026-03-06': 'limit_up_20260306.csv',
    }
    dfs = []
    for date, filename in history_files.items():
        try:
            df = pd.read_csv(filename)
            df['日期'] = date
            dfs.append(df)
        except:
            pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

st.title('📈 A股涨停板监控')
st.markdown(f'**更新时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# 标签页切换
tab1, tab2 = st.tabs(['📅 今日数据', '📊 历史数据'])

with tab1:
    try:
        df = get_limit_up_stocks()
        if df.empty:
            st.warning('今日无涨停数据')
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('涨停家数', len(df))
            with col2:
                st.metric('创业板', len(df[df['市场'] == '创业板']))
            with col3:
                st.metric('科创板', len(df[df['市场'] == '科创板']))
            st.divider()
            st.bar_chart(df['市场'].value_counts())
            st.divider()
            search_term = st.text_input('🔍 搜索股票代码或名称', '', key='today_search')
            if search_term:
                filtered = df[df['代码'].str.contains(search_term) | df['名称'].str.contains(search_term)]
                st.dataframe(filtered, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f'获取数据失败: {e}')

with tab2:
    st.header('历史涨停板数据')
    history_df = load_history_data()
    if history_df.empty:
        st.info('暂无历史数据')
    else:
        # 按日期统计
        daily_stats = history_df.groupby('日期').size()
        st.subheader('📈 每日涨停家数趋势')
        st.line_chart(daily_stats)
        
        st.subheader('📋 历史涨停股票')
        st.dataframe(history_df, use_container_width=True)
        
        # 按日期筛选
        date_filter = st.selectbox('选择日期', ['全部'] + list(history_df['日期'].unique()))
        if date_filter != '全部':
            filtered = history_df[history_df['日期'] == date_filter]
            st.subheader(f'{date_filter} 涨停股票 ({len(filtered)}只)')
            st.dataframe(filtered, use_container_width=True)
