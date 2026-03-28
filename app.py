import streamlit as st
import json
import base64
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

# --- 1. 雲端核心配置 ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_PATH = "bible_reading_v27.json"
FONT_FILE = "msjh.ttc"  # 提醒：請確保 GitHub 上有這個字體檔

def load_from_cloud():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            res = r.json()
            content = base64.b64decode(res["content"]).decode("utf-8")
            return json.loads(content), res["sha"]
    except:
        pass
    return {"current_year": "2", "members": {}}, None

def save_to_cloud(data, sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {"message": "Final Update from Mobile", "content": content_b64, "sha": sha}
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code == 200

if 'data' not in st.session_state:
    st.session_state.data, st.session_state.sha = load_from_cloud()

data = st.session_state.data

# --- 2. 介面設定 ---
st.set_page_config(page_title="讀經管理雲端版", layout="wide")
st.title("📖 讀經進度管理系統")

# 選擇年度與週數 (主要操作區)
with st.container():
    c1, c2, c3 = st.columns(3)
    curr_y = c1.selectbox("年度", ["1", "2", "3", "4"], index=int(data.get("current_year", "2"))-1)
    curr_q = c2.selectbox("季度", ["1", "2", "3", "4"])
    weeks_in_q = list(range((int(curr_q)-1)*13 + 1, int(curr_q)*13 + 1))
    sel_w = c3.selectbox("當前週數", weeks_in_q)

# --- 3. 點選簽到區 ---
m_ids = sorted(data["members"].keys(), key=lambda x: int(x))
done_ids = [m for m, info in data["members"].items() if int(sel_w) in info["progress"].get(str(curr_y), [])]

st.write(f"### 📍 第 {sel_w} 週 點選簽到 ({len(done_ids)} / {len(m_ids)})")
cols = st.columns(3)
for i, mid in enumerate(m_ids):
    name = data["members"][mid]["name"]
    is_done = mid in done_ids
    if cols[i % 3].button(f"{name}", key=f"btn_{mid}", use_container_width=True, type="primary" if is_done else "secondary"):
        prog = data["members"][mid].setdefault("progress", {}).setdefault(str(curr_y), [])
        if int(sel_w) in prog: prog.remove(int(sel_w))
        else: prog.append(int(sel_w)); prog.sort()
        st.rerun()

st.divider()

# --- 4. 圖片生成區 (仿電腦版) ---
st.subheader("🖼️ 生成區間統計圖片")
r1, r2 = st.columns(2)
start_w = r1.number_input("起始週", value=weeks_in_q[0], min_value=1, max_value=52)
end_w = r2.number_input("結束週", value=sel_w, min_value=1, max_value=52)

def draw_stats_image(data, year, start_w, end_w):
    try:
        if os.path.exists(FONT_FILE):
            f_title = ImageFont.truetype(FONT_FILE, 24)
            f_text = ImageFont.truetype(FONT_FILE, 18)
        else:
            f_title = f_text = ImageFont.load_default()
    except:
        f_title = f_text = ImageFont.load_default()

    m_list = sorted(data["members"].keys(), key=lambda x: int(x))
    num_w = end_w - start_w + 1
    c_w, c_h = 45, 35
    n_w = 120
    m = 25
    img_w = n_w + num_w * c_w + m * 2
    img_h = (len(m_list) + 3) * c_h + m * 2
    img = Image.new('RGB', (img_w, img_h), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # 畫表頭與數據 (簡化邏輯，確保格式整齊)
    d.text((m, m), f"第 {year} 年 第 {start_w}-{end_w} 週 讀經統計表", fill=(0,0,0), font=f_title)
    y = m + 50
    d.text((m+10, y), "姓名", fill=(0,0,0), font=f_text)
    for i, w in enumerate(range(start_w, end_w + 1)):
        d.text((m + n_w + i*c_w + 5, y), f"W{w:02d}", fill=(0,0,0), font=f_text)
    
    y += c_h
    for mid in m_list:
        name = data["members"][mid]["name"]
        prog = data["members"][mid]["progress"].get(str(year), [])
        d.line([(m, y), (img_w-m, y)], fill=(220,220,220))
        d.text((m+10, y+5), name, fill=(0,0,0), font=f_text)
        for i, w in enumerate(range(start_w, end_w + 1)):
            if w in prog:
                d.text((m + n_w + i*c_w + 15, y+5), "V", fill=(0,120,0), font=f_text)
        y += c_h
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if st.button("📊 生成並下載統計圖片", use_container_width=True):
    img_bytes = draw_stats_image(data, curr_y, int(start_w), int(end_w))
    st.image(img_bytes)
    st.download_button("📥 點此儲存圖片到手機", img_bytes, f"Report_W{start_w}_{end_w}.png", "image/png", use_container_width=True)

st.divider()

# --- 5. 人員管理與存檔 (這一區絕對在！) ---
st.subheader("⚙️ 系統管理")
c_save, c_manage = st.columns(2)

with c_save:
    if st.button("💾 儲存所有變更至雲端", type="primary", use_container_width=True):
        if save_to_cloud(data, st.session_state.sha):
            st.success("✅ 同步成功！")
            _, new_sha = load_from_cloud()
            st.session_state.sha = new_sha
        else:
            st.error("❌ 同步失敗")

with c_manage:
    with st.expander("👤 人員名單管理 (展開新增/刪除)"):
        # 新增
        new_name = st.text_input("新增人員姓名")
        if st.button("➕ 執行新增"):
            if new_name:
                new_id = f"{max([int(k) for k in data['members'].keys()] + [0]) + 1:02d}"
                data["members"][new_id] = {"name": new_name, "progress": {}}
                st.success(f"已加入 {new_name}")
                st.rerun()
        
        st.divider()
        # 刪除
        del_target = st.selectbox("選擇要刪除的人員", ["-- 請選擇 --"] + [f"{k}: {v['name']}" for k, v in data["members"].items()])
        if st.button("🗑️ 執行刪除", type="secondary"):
            if "-- 請選擇 --" not in del_target:
                tid = del_target.split(":")[0]
                tname = data['members'][tid]['name']
                del data["members"][tid]
                st.warning(f"已刪除 {tname}，記得按儲存。")
                st.rerun()
