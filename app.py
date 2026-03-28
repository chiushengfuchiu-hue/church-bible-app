import streamlit as st
import json
import base64
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime

# --- 1. 雲端核心配置 ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_PATH = "bible_reading_v27.json"

def load_from_cloud():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        res = r.json()
        content = base64.b64decode(res["content"]).decode("utf-8")
        return json.loads(content), res["sha"]
    return None, None

def save_to_cloud(data, sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {"message": "Update from Mobile", "content": content_b64, "sha": sha}
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code == 200

if 'data' not in st.session_state:
    st.session_state.data, st.session_state.sha = load_from_cloud()

data = st.session_state.data

# --- 2. 標題與基本設定 ---
st.set_page_config(page_title="讀經簽到雲端版", layout="wide")
st.title("📖 讀經進度管理 & 簽到系統")

with st.expander("📅 選擇年度與週數"):
    col_y, col_q, col_w = st.columns(3)
    curr_y = col_y.selectbox("年度", ["1", "2", "3", "4"], index=int(data.get("current_year", "2"))-1)
    curr_q = col_q.selectbox("季度", ["1", "2", "3", "4"])
    weeks = list(range((int(curr_q)-1)*13 + 1, int(curr_q)*13 + 1))
    sel_w = col_w.selectbox("週數", weeks)

# --- 3. 快速點選區 (主操作) ---
st.subheader(f"📍 第 {curr_y} 年 第 {sel_w} 週 點選簽到")
m_ids = sorted(data["members"].keys(), key=lambda x: int(x))
done_ids = [m for m, info in data["members"].items() if int(sel_w) in info["progress"].get(str(curr_y), [])]

# 顯示進度條
progress_val = len(done_ids) / len(m_ids) if m_ids else 0
st.progress(progress_val)
st.write(f"📊 目前完成率：{len(done_ids)} / {len(m_ids)}")

cols = st.columns(3) # 手機版自動適應
for i, mid in enumerate(m_ids):
    name = data["members"][mid]["name"]
    is_done = mid in done_ids
    if cols[i % 3].button(f"{name}", key=f"btn_{mid}", use_container_width=True, type="primary" if is_done else "secondary"):
        prog = data["members"][mid]["progress"].setdefault(str(curr_y), [])
        if int(sel_w) in prog: prog.remove(int(sel_w))
        else: prog.append(int(sel_w)); prog.sort()
        st.rerun()

st.divider()

# --- 4. 統計圖表區 (仿電腦版) ---
st.subheader("📊 當週統計報表")
report_list = []
for mid in m_ids:
    name = data["members"][mid]["name"]
    is_done = "✅ 已完成" if int(sel_w) in data["members"][mid]["progress"].get(str(curr_y), []) else "⬜ 未完成"
    report_list.append({"姓名": name, "狀態": is_done})

df = pd.DataFrame(report_list)
st.table(df) # 網頁直接顯示表格，方便截圖

# --- 5. 功能按鈕區 ---
st.divider()
c1, c2 = st.columns(2)

if c1.button("💾 儲存並同步雲端", type="primary", use_container_width=True):
    if save_to_cloud(data, st.session_state.sha):
        st.success("同步成功！")
        _, new_sha = load_from_cloud()
        st.session_state.sha = new_sha
    else:
        st.error("同步失敗")

# 下載 JSON 備份 (作為圖片外的另一種保障)
json_str = json.dumps(data, ensure_ascii=False, indent=2)
c2.download_button("📥 下載資料備份", json_str, "bible_backup.json", "application/json", use_container_width=True)

with st.expander("👤 人員管理"):
    new_n = st.text_input("新增姓名")
    if st.button("➕ 執行新增"):
        if new_n:
            new_id = f"{max([int(k) for k in data['members'].keys()] + [0]) + 1:02d}"
            data["members"][new_id] = {"name": new_n, "progress": {}}
            st.rerun()
