import streamlit as st
import json
import base64
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- 1. 雲端資料核心配置 ---
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
    payload = {"message": "Mobile Update", "content": content_b64, "sha": sha}
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code == 200

if 'data' not in st.session_state:
    st.session_state.data, st.session_state.sha = load_from_cloud()

data = st.session_state.data

# --- 2. 側邊欄：功能選單 ---
with st.sidebar:
    st.title("⚙️ 管理選單")
    curr_y = st.selectbox("選擇年度", ["1", "2", "3", "4"], index=int(data.get("current_year", "2"))-1)
    curr_q = st.selectbox("選擇季度", ["1", "2", "3", "4"], index=0)
    q_idx = int(curr_q)
    weeks = list(range((q_idx-1)*13 + 1, q_idx*13 + 1))
    sel_w = st.selectbox("選擇週數", weeks)
    
    st.divider()
    if st.button("💾 儲存所有變更至雲端", type="primary", use_container_width=True):
        if save_to_cloud(data, st.session_state.sha):
            st.success("同步成功！")
            _, new_sha = load_from_cloud()
            st.session_state.sha = new_sha
        else:
            st.error("同步失敗")

# --- 3. 主畫面：功能切換 ---
tab1, tab2 = st.tabs(["📝 進度勾選", "📋 聚會簽到表"])

with tab1:
    st.subheader(f"第 {curr_y} 年 第 {sel_w} 週 進度點選")
    done_ids = [m for m, info in data["members"].items() if int(sel_w) in info["progress"].get(str(curr_y), [])]
    
    m_ids = sorted(data["members"].keys(), key=lambda x: int(x))
    cols = st.columns(3)
    for i, mid in enumerate(m_ids):
        name = data["members"][mid]["name"]
        is_done = mid in done_ids
        if cols[i % 3].button(f"{name}", key=f"check_{mid}", use_container_width=True, type="primary" if is_done else "secondary"):
            prog = data["members"][mid]["progress"].setdefault(str(curr_y), [])
            if int(sel_w) in prog: prog.remove(int(sel_w))
            else: prog.append(int(sel_w)); prog.sort()
            st.rerun()

with tab2:
    st.subheader(f"📅 第 {sel_w} 週 聚會簽到/讀經報表")
    
    # 建立簽到表格數據
    report_list = []
    for mid in sorted(data["members"].keys(), key=lambda x: int(x)):
        name = data["members"][mid]["name"]
        status = "✅ 已讀經/已簽到" if int(sel_w) in data["members"][mid]["progress"].get(str(curr_y), []) else "⬜ 尚未簽到"
        report_list.append({"編號": mid, "姓名": name, "狀態": status})
    
    df = pd.DataFrame(report_list)
    
    # 顯示美化表格
    st.table(df)
    
    # 下載功能
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載此週簽到表 (Excel/CSV)",
        data=csv,
        file_name=f"Sign_in_Week_{sel_w}.csv",
        mime="text/csv",
        use_container_width=True
    )

# --- 4. 人員管理 (移至下方) ---
with st.expander("👤 人員名單編輯"):
    col_add, col_del = st.columns(2)
    with col_add:
        new_n = st.text_input("新增姓名")
        if st.button("➕ 新增"):
            if new_n:
                new_id = f"{max([int(k) for k in data['members'].keys()] + [0]) + 1:02d}"
                data["members"][new_id] = {"name": new_n, "progress": {}}
                st.rerun()
    with col_del:
        del_id = st.text_input("刪除代碼")
        if st.button("🗑️ 刪除"):
            if del_id in data["members"]:
                del data["members"][del_id]
                st.rerun()
