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
FONT_FILE = "msjh.ttc"  # 請確保此字體檔已上傳至 GitHub

def load_from_cloud():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        res = r.json()
        content = base64.b64decode(res["content"]).decode("utf-8")
        return json.loads(content), res["sha"]
    return {"current_year": "2", "members": {}}, None

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

# --- 2. 介面設定與操作 ---
st.set_page_config(page_title="讀經管理雲端版", layout="wide")
st.title("📖 讀經進度管理系統")

with st.container():
    c1, c2, c3 = st.columns(3)
    curr_y = c1.selectbox("年度", ["1", "2", "3", "4"], index=int(data.get("current_year", "2"))-1)
    curr_q = c2.selectbox("季度", ["1", "2", "3", "4"])
    weeks_in_q = list(range((int(curr_q)-1)*13 + 1, int(curr_q)*13 + 1))
    sel_w = c3.selectbox("當前週數", weeks_in_q)

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

# --- 3. 終極圖片生成區 (仿電腦版) ---
st.subheader("🖼️ 生成區間統計圖片")
r1, r2 = st.columns(2)
start_w = r1.number_input("起始週", value=weeks_in_q[0], min_value=1, max_value=52)
end_w = r2.number_input("結束週", value=sel_w, min_value=1, max_value=52)

# 繪圖函數
def draw_stats_image(data, year, start_w, end_w):
    # 設定字體
    try:
        if os.path.exists(FONT_FILE):
            font_title = ImageFont.truetype(FONT_FILE, 24)
            font_text = ImageFont.truetype(FONT_FILE, 18)
        else:
            # 如果沒抓到字體，使用預設 (中文會變亂碼，所以一定要上傳字體)
            font_title = font_text = ImageFont.load_default()
            st.warning("⚠️ 找不到字體檔 msjh.ttc，圖片中文將無法顯示。")
    except:
        font_title = font_text = ImageFont.load_default()

    # 計算圖片尺寸
    m_ids = sorted(data["members"].keys(), key=lambda x: int(x))
    num_weeks = end_w - start_w + 1
    cell_w, cell_h = 40, 30
    name_w = 100
    margin = 20
    
    img_w = name_w + num_weeks * cell_w + margin * 2
    img_h = (len(m_ids) + 3) * cell_h + margin * 2
    
    # 創建畫布
    img = Image.new('RGB', (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 繪製標題
    title_text = f"第 {year} 年 第 {start_w} - {end_w} 週 讀經統計表"
    draw.text((margin, margin), title_text, fill=(0, 0, 0), font=font_title)
    
    # 繪製表頭
    y_offset = margin + 40
    draw.text((margin + 10, y_offset), "姓名", fill=(0, 0, 0), font=font_text)
    for i, w in enumerate(range(start_w, end_w + 1)):
        draw.text((margin + name_w + i * cell_w + 5, y_offset), f"W{w:02d}", fill=(0, 0, 0), font=font_text)
    
    # 繪製格子與內容
    y_offset += cell_h
    for mid in m_ids:
        name = data["members"][mid]["name"]
        prog = data["members"][mid]["progress"].get(str(year), [])
        
        # 畫水平線
        draw.line([(margin, y_offset), (img_w - margin, y_offset)], fill=(200, 200, 200), width=1)
        
        # 畫姓名
        draw.text((margin + 10, y_offset + 5), name, fill=(0, 0, 0), font=font_text)
        
        # 畫進度
        for i, w in enumerate(range(start_w, end_w + 1)):
            if w in prog:
                # 畫一個綠色打勾 V
                draw.text((margin + name_w + i * cell_w + 10, y_offset + 5), "V", fill=(0, 150, 0), font=font_text)
            
            # 畫垂直線 (格子)
            if i == 0: # 畫第一條
                draw.line([(margin + name_w, y_offset - cell_h), (margin + name_w, img_h - margin - cell_h)], fill=(200, 200, 200), width=1)
            draw.line([(margin + name_w + (i+1) * cell_w, y_offset - cell_h), (margin + name_w + (i+1) * cell_w, img_h - margin - cell_h)], fill=(200, 200, 200), width=1)

        y_offset += cell_h

    # 畫框線
    draw.rectangle([(margin, margin + 40), (img_w - margin, img_h - margin - cell_h)], outline=(0, 0, 0), width=1)

    # 轉為 Bytes
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if st.button("🖼️ 生成並預覽統計圖片", use_container_width=True):
    with st.spinner("圖片生成中，請稍候..."):
        img_bytes = draw_stats_image(data, curr_y, start_w, end_w)
        
        # 在網頁上顯示圖片預覽
        st.image(img_bytes, caption=f"Report_W{start_w}_{end_w}.png")
        
        # 真正的下載按鈕 (手機版用這個下載圖片最穩定)
        st.download_button(
            label="📥 下載此統計圖片 (PNG)",
            data=img_bytes,
            file_name=f"Bible_Report_W{start_w}_{end_w}.png",
            mime="image/png",
            use_container_width=True
        )

st.divider()

# --- 4. 系統管理與存檔 (移至下方) ---
# ... (保持原本的新增/刪除人員程式碼即可) ...
