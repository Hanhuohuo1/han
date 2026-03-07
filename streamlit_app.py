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
    """Load historical limit up data"""
    history_files = {
        '2026-03-06': 'limit_up_20260306.csv',
    }
    dfs = []
    for date, filename in history_files.items():
        try:
            df = pd.read_csv(filename)
            # 统一列名
            column_map = {
                'code': '代码',
                'name': '名称', 
                'close': '收盘价',
                'pct_change': '涨幅(%)'
            }
            df = df.rename(columns=column_map)
            df['日期'] = date
            # 确保有代码列
            if '代码' in df.columns:
                df['代码'] = df['代码'].astype(str).str.replace('.SZ', '').str.replace('.SH', '')
            dfs.append(df)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

st.title('📈 A股涨停板监控')
st.markdown(f'**更新时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

tab1, tab2, tab3, tab4 = st.tabs(['📅 今日数据', '📊 历史数据', '📉 K线图', '🎯 每日选股'])

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
    
    df = pd.DataFrame()
    
    if data_source == '今日涨停':
        try:
            df = get_limit_up_stocks()
        except:
            pass
    else:
        try:
            df = load_history_data()
        except:
            pass
    
    if df is not None and not df.empty:
        # 获取股票列表
        if '代码' in df.columns:
            stock_list = df['代码'].astype(str).unique().tolist()
        else:
            stock_list = []
        
        if stock_list:
            selected_code = st.selectbox('选择股票', stock_list, key='kline_stock')
            
            if selected_code:
                # 获取股票名称
                if data_source == '今日涨停' and '名称' in df.columns:
                    stock_name = df[df['代码'].astype(str) == selected_code]['名称'].values
                    stock_name = stock_name[0] if len(stock_name) > 0 else selected_code
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

with tab4:
    st.header('🎯 每日选股推荐')
    st.markdown('基于AI模型实时分析市场热点，推荐潜力股票')
    
    if st.button('🔄 获取今日推荐', key='get_recommend'):
        with st.spinner('AI正在分析市场...'):
            try:
                # 获取市场数据
                urls = [
                    'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f1,f2,f3,f4,f12,f13,f14',
                    'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f1,f2,f3,f4,f12,f13,f14',
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
                    except:
                        continue
                
                # 简单的选股策略：涨幅2%-8%，有成交量支撑
                candidates = []
                for d in all_stocks:
                    pct = d.get('f3', 0)
                    vol = d.get('f4', 0) or 0
                    code = d.get('f12', '')
                    name = d.get('f14', '')
                    close = d.get('f2', 0)
                    
                    # 筛选条件：涨幅2%-8%，非涨停
                    if 2 <= pct <= 8 and vol > 50000000:
                        market = ''
                        if code.startswith('300') or code.startswith('301'):
                            market = '创业板'
                        elif code.startswith('688'):
                            market = '科创板'
                        elif code.startswith('600') or code.startswith('601') or code.startswith('603'):
                            market = '沪市主板'
                        elif code.startswith('000') or code.startswith('002'):
                            market = '深市主板'
                        else:
                            market = '其他'
                        
                        # 计算得分
                        score = pct * 10 + vol / 10000000  # 涨幅和成交量加权
                        candidates.append({
                            '代码': code,
                            '名称': name,
                            '收盘价': close,
                            '涨幅(%)': round(pct, 2),
                            '市场': market,
                            '得分': round(score, 2)
                        })
                
                if candidates:
                    # 按得分排序，取前10
                    rec_df = pd.DataFrame(candidates)
                    rec_df = rec_df.sort_values('得分', ascending=False).head(10)
                    rec_df = rec_df.reset_index(drop=True)
                    
                    st.success(f'✅ 找到 {len(rec_df)} 只潜力股票')
                    
                    # 显示推荐股票
                    st.subheader('🌟 今日推荐股票')
                    
                    for i, row in rec_df.iterrows():
                        with st.expander(f"{i+1}. {row['名称']} ({row['代码']}) - 涨幅 {row['涨幅(%)']}%"):
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric('现价', f"{row['收盘价']:.2f}")
                            with col2:
                                st.metric('涨幅', f"{row['涨幅(%)']:.2f}%")
                            with col3:
                                st.metric('市场', row['市场'])
                            with col4:
                                st.metric('综合得分', row['得分'])
                            
                            # 获取实时盘口数据
                            try:
                                if row['代码'].startswith('6'):
                                    secid = f"1.{row['代码']}"
                                else:
                                    secid = f"0.{row['代码']}"
                                
                                detail_url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f2,f3,f4,f5,f6,f8,f10,f12,f13,f14,f15,f16,f17,f18'
                                req = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
                                resp = urllib.request.urlopen(req, timeout=10)
                                detail = json.loads(resp.read().decode('utf-8'))
                                data = detail.get('data', {})
                                
                                st.subheader('📊 实时盘口')
                                c1, c2, c3, c4 = st.columns(4)
                                with c1:
                                    st.metric('最高', data.get('f4', '-'))
                                with c2:
                                    st.metric('最低', data.get('f5', '-'))
                                with c3:
                                    st.metric('成交量', f"{data.get('f6', 0)/10000:.0f}万")
                                with c4:
                                    st.metric('成交额', f"{data.get('f8', 0)/100000000:.2f}亿")
                                
                                # 买卖盘口
                                st.subheader('🟢 卖盘 (Top 5)')
                                # 这里需要另外的API，简化显示
                                st.info('详细盘口数据需要更多API支持')
                                
                            except Exception as e:
                                st.warning(f'实时数据获取失败: {e}')
                else:
                    st.warning('暂无符合条件的推荐股票')
                    
            except Exception as e:
                st.error(f'获取推荐失败: {e}')
    
    # 默认显示说明
    st.info('👆 点击上方按钮获取今日AI推荐股票，基于涨幅、成交量等指标综合评分')
