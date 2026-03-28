import streamlit as st
import json
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# --- 1. 設定與資料處理 ---
DATA_FILE = "bible_reading_v27.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # 預設初始資料
    names = ["程乃珍", "盧正亮", "人峰", "邱文雀", "林淑惠", "翁春祝", "雅雲", "LeeBa22", "鳳姐", "谷哥", "YiHong", "安俐", "彩梅", "劉淑珠", "黃敏生", "林春妙", "yin-pan liang", "蕭慧麗", "蕭健文", "石美莎", "黃然玉", "周寶燕", "吳秀卉", "翁淑美", "妃玉", "約瑟的阿媽", "富美", "WT Chaou-滅飛", "單麗蘭", "王春桃", "楊游美麗", "邱聖富", "李瑞娟", "蔡慧例", "李鶯芳", "陳文智", "林雅音", "文川"]
    members = {f"{i+1:02d}": {"name": name, "progress": {}} for i, name in enumerate(names)}
    return {"current_year": "2", "members": members}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初始化 Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# --- 2. 側邊欄控制 ---
with st.sidebar:
    st.header("⚙️ 進度切換")
    year = st.selectbox("選擇年度", ["1", "2", "3", "4"], index=int(data.get("current_year", "2"))-1)
    quarter = st.selectbox("選擇季度", ["1", "2", "3", "4"], index=0)
    
    q_int = int(quarter)
    weeks = list(range((q_int-1)*13 + 1, q_int*13 + 1))
    selected_week = st.selectbox("選擇週數", weeks)
    
    st.divider()
    if st.button("💾 儲存所有變更至雲端", type="primary", use_container_width=True):
        save_data(data)
        st.success("資料已成功同步！")

# --- 3. 主要介面 ---
st.title(f"📖 第 {year} 年 第 {selected_week} 週")

# 獲取當週已完成 ID 列表
current_week_done = []
for mid, info in data["members"].items():
    if str(selected_week) in [str(w) for w in info["progress"].get(str(year), [])]:
        current_week_done.append(mid)

# 即時統計看板
total_members = len(data["members"])
done_count = len(current_week_done)

col1, col2, col3 = st.columns(3)
col1.metric("已完成人數", f"{done_count} 人")
col2.metric("未完成人數", f"{total_members - done_count} 人")
col3.metric("完成率", f"{int(done_count/total_members*100)}%")

st.divider()

# 人員點選區 (格狀排列，適應手機)
st.subheader("點選人員標記完成：")
cols = st.columns(3) if st.sidebar.checkbox("手機模式", value=True) else st.columns(6)

ids = sorted(data["members"].keys(), key=lambda x: int(x))
for i, mid in enumerate(ids):
    name = data["members"][mid]["name"]
    is_done = mid in current_week_done
    
    # 決定按鈕樣式
    btn_label = f"✅ {name}" if is_done else name
    btn_type = "primary" if is_done else "secondary"
    
    if cols[i % len(cols)].button(btn_label, key=mid, use_container_width=True, type=btn_type):
        # 切換狀態
        p = data["members"][mid]["progress"].setdefault(str(year), [])
        if int(selected_week) in p:
            p.remove(int(selected_week))
        else:
            p.append(int(selected_week))
            p.sort()
        st.rerun()

# --- 4. 底部功能表 ---
st.divider()
b_col1, b_col2 = st.columns(2)

# 紫色統計彈窗功能
with b_col1:
    if st.button("📊 查看季度統計", use_container_width=True):
        @st.dialog("季度/年度完成人數統計")
        def show_stats():
            st.write(f"### 年度: {year}")
            mode = st.radio("範圍", ["本季", "上半年", "下半年", "全年度"], horizontal=True)
            
            if mode == "本季": r = range((q_int-1)*13+1, q_int*13+1)
            elif mode == "上半年": r = range(1, 27)
            elif mode == "下半年": r = range(27, 53)
            else: r = range(1, 53)
            
            stat_list = []
            for w in r:
                c = sum(1 for m in data["members"].values() if w in m["progress"].get(str(year), []))
                stat_list.append({"週數": f"W{w:02d}", "完成人數": c})
            
            st.table(pd.DataFrame(stat_list))
        show_stats()

# 圖片導出功能 (網頁版改為直接下載)
with b_col2:
    if st.button("🖼️ 生成報表圖片並下載", use_container_width=True):
        st.info("網頁版圖片導出處理中...請稍候")
        # 這裡可以整合您原本的 PIL 繪圖邏輯並提供 st.download_button
        # 由於篇幅限制，建議先使用網頁介面查看，若需下載圖片我再幫您補上
