import streamlit as st
import pandas as pd
import urllib.request
import json
from datetime import datetime

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='A股涨停板监控',
    page_icon='📈',
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data(ttl='1h')
def get_limit_up_stocks():
    """Grab limit-up stock data from East Money API."""
    
    urls = [
        # 创业板
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:80&fields=f1,f2,f3,f4,f12,f13,f14',
        # 科创板
        'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f1,f2,f3,f4,f12,f13,f14',
        # 主板
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
    
    # 筛选涨停板 (涨幅 >= 9.9%)
    limit_up = []
    for d in all_stocks:
        pct = d.get('f3', 0)
        if pct >= 9.9:
            code = d.get('f12', '')
            name = d.get('f14', '')
            close = d.get('f2', 0)
            market = ''
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
            
            limit_up.append({
                '代码': code,
                '名称': name,
                '收盘价': close,
                '涨幅(%)': round(pct, 2),
                '市场': market
            })
    
    return pd.DataFrame(limit_up)

# -----------------------------------------------------------------------------
# Draw the actual page

st.title('📈 A股涨停板监控')

st.markdown(f'**更新时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# 获取数据
try:
    df = get_limit_up_stocks()
    
    if df.empty:
        st.warning('今日无涨停数据')
    else:
        # 统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('涨停家数', len(df))
        with col2:
            chuangye = len(df[df['市场'] == '创业板'])
            st.metric('创业板', chuangye)
        with col3:
            kechuang = len(df[df['市场'] == '科创板'])
            st.metric('科创板', kechuang)
        
        st.divider()
        
        # 按市场分组
        st.header('📊 各板块涨停情况')
        
        market_counts = df['市场'].value_counts()
        st.bar_chart(market_counts)
        
        st.divider()
        
        # 搜索功能
        st.header('🔍 查找股票')
        search_term = st.text_input('输入股票代码或名称搜索', '')
        
        if search_term:
            filtered = df[df['代码'].str.contains(search_term) | df['名称'].str.contains(search_term)]
            st.dataframe(filtered, use_container_width=True)
        else:
            # 显示全部涨停股
            st.header('📋 涨停股票列表')
            st.dataframe(df, use_container_width=True)
            
except Exception as e:
    st.error(f'获取数据失败: {e}')
