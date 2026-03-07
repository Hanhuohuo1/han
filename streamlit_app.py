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

@st.cache_data(ttl='1d')
def get_kline_data(code):
    """获取K线数据"""
    try:
        # 转换代码格式
        if code.startswith('6'):
            secid = f'1.{code}'
        else:
            secid = f'0.{code}'
        
        url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&beg=0&end=20500101&lmt=1000'
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read().decode('utf-8'))
        
        klines = data.get('data', {}).get('klines', [])
        if not klines:
            return None
            
        records = []
        for kline in klines:
            parts = kline.split(',')
            records.append({
                '日期': parts[0],
                '开盘': float(parts[1]),
                '收盘': float(parts[2]),
                '最高': float(parts[3]),
                '最低': float(parts[4]),
                '成交量': float(parts[5]),
                '成交额': float(parts[6]) if len(parts) > 6 else 0,
                '振幅': float(parts[7]) if len(parts) > 7 else 0,
                '涨跌幅': float(parts[8]) if len(parts) > 8 else 0,
                '涨跌额': float(parts[9]) if len(parts) > 9 else 0,
                '换手率': float(parts[10]) if len(parts) > 10 else 0,
            })
        return pd.DataFrame(records)
    except Exception as e:
        print(f"Error getting K-line: {e}")
        return None

def load_history_data():
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

tab1, tab2, tab3 = st.tabs(['📅 今日数据', '📊 历史数据', '📉 K线图'])

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
        daily_stats = history_df.groupby('日期').size()
        st.subheader('📈 每日涨停家数趋势')
        st.line_chart(daily_stats)
        st.subheader('📋 历史涨停股票')
        st.dataframe(history_df, use_container_width=True)
        date_filter = st.selectbox('选择日期', ['全部'] + list(history_df['日期'].unique()), key='date_filter')
        if date_filter != '全部':
            filtered = history_df[history_df['日期'] == date_filter]
            st.subheader(f'{date_filter} 涨停股票 ({len(filtered)}只)')
            st.dataframe(filtered, use_container_width=True)

with tab3:
    st.header('📉 个股K线图')
    
    # 数据来源选择
    data_source = st.radio('选择数据来源', ['今日涨停', '历史涨停'], horizontal=True)
    
    if data_source == '今日涨停':
        df = get_limit_up_stocks()
    else:
        df = load_history_data()
    
    if df is not None and not df.empty:
        stock_list = df['代码'].unique().tolist()
        selected_code = st.selectbox('选择股票', stock_list, key='kline_stock')
        
        if selected_code:
            # 获取股票名称
            if data_source == '今日涨停':
                stock_name = df[df['代码'] == selected_code]['名称'].values[0]
            else:
                stock_name = selected_code
            
            st.subheader(f'{stock_name} ({selected_code}) K线图')
            
            # 获取K线数据
            kline_df = get_kline_data(selected_code)
            
            if kline_df is not None and not kline_df.empty:
                # 显示最近20天数据
                recent_df = kline_df.tail(30)
                
                # 简化的K线展示 - 用表格+涨跌幅颜色
                st.subheader('最近30个交易日')
                
                def color_change(val):
                    color = 'green' if val > 0 else 'red' if val < 0 else 'black'
                    return f'color: {color}'
                
                display_df = recent_df[['日期', '开盘', '收盘', '最高', '最低', '涨跌幅', '成交量']].copy()
                st.dataframe(display_df.style.applymap(color_change, subset=['涨跌幅']), use_container_width=True)
                
                # 简单的折线图展示
                st.subheader('收盘价走势')
                st.line_chart(recent_df.set_index('日期')['收盘'])
                
                st.subheader('成交量走势')
                st.bar_chart(recent_df.set_index('日期')['成交量'])
            else:
                st.warning('暂无K线数据')
    else:
        st.info('暂无数据，无法查看K线')
