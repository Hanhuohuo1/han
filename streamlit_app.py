import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

st.set_page_config(page_title="A股涨停板分析", layout="wide")
st.title("📈 A股涨停板实时分析")

# 自动读取最新的 CSV 文件
csv_files = glob.glob('limit_up_*.csv')
if csv_files:
    latest = max(csv_files, key=os.path.getctime)
    df = pd.read_csv(latest)
    st.success(f"加载数据：{latest}，共 {len(df)} 只涨停股")
else:
    st.warning("没有找到数据文件，请先运行数据抓取脚本")
    st.stop()

# 展示原始数据
with st.expander("查看原始数据"):
    st.dataframe(df)

# 涨幅分布直方图
st.subheader("涨幅分布")
fig, ax = plt.subplots()
df['pct_change'].hist(bins=100, edgecolor='black', ax=ax)
ax.set_xlabel("涨幅 (%)")
ax.set_ylabel("数量")
st.pyplot(fig)

# 成交量前10
st.subheader("成交量前10的股票")
top10 = df.nlargest(10, 'volume')[['name', 'volume']]
fig2, ax2 = plt.subplots()
ax2.barh(top10['name'], top10['volume'])
ax2.set_xlabel("成交量")
st.pyplot(fig2)
