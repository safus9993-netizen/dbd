import streamlit as st
import pandas as pd
import database as db
import re
from datetime import datetime

st.set_page_config(page_title="公司訂便當系統", page_icon="🍱", layout="wide")

# 介面自訂美化 CSS
st.markdown("""
<style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    div[data-testid="stSidebarNav"] { padding-top: 1rem; }
    .stTextInput>div>div>input[type="password"] { border: 2px solid #ef4444; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🍱 訂便當系統")
page = st.sidebar.radio("📌 導覽清單", ["🍽️ 員工點餐", "📊 訂單總覽與結帳", "⚙️ 餐廳與揪團管理"])

if page == "⚙️ 餐廳與揪團管理":
    st.header("⚙️ 餐廳與揪團系統設定 (管理員/發起人專區)")
    
    # 🔒 管理員帳密驗證
    st.info("💡 請輸入管理員帳號與密碼解鎖權限。")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        admin_user = st.text_input("👤 管理員帳號：", key="user_admin")
    with col_l2:
        admin_pwd = st.text_input("🔒 管理員密碼：", type="password", key="pwd_admin")
    
    if db.verify_admin(admin_user, admin_pwd):
        st.success(f"✅ 歡迎回來，{admin_user}！已解鎖管理員權限。")
        st.markdown("---")
        
        # --- 管理員功能區塊 ---
        # 0. 帳號維護區
        with st.expander("👥 管理員帳號設定 (新增/刪除帳號)"):
            c_new1, c_new2, c_new3 = st.columns([2, 2, 1])
            with c_new1:
                new_usr = st.text_input("新增帳號", key="new_u", placeholder="自訂新管理員帳號")
            with c_new2:
                new_pwd = st.text_input("新增密碼", key="new_p", type="password")
            with c_new3:
                st.write("")
                st.write("")
                if st.button("➕ 新增管理員", use_container_width=True):
                    if new_usr.strip() and new_pwd.strip():
                        if db.add_admin(new_usr.strip(), new_pwd.strip()):
                            st.success("建立成功！")
                            st.rerun()
                        else:
                            st.error("⚠️ 該帳號已存在！")
                    else:
                        st.error("請完整填寫")
            
            st.write("---")
            st.write("**目前系統管理員：**")
            admins_df = db.get_admins()
            for _, row in admins_df.iterrows():
                ca1, ca2 = st.columns([4, 1])
                ca1.write(f"👤 {row['username']}")
                if ca2.button("🗑️ 撤銷權限", key=f"del_adm_{row['id']}"):
                    if db.delete_admin(row['id']):
                        st.toast("已撤銷該管理員權限")
                        st.rerun()
                    else:
                        st.error("⚠️ 無法刪除！系統至少需要保留一名管理員。")

        # 1. 揪團開團
        st.markdown("### 📣 第一步：發起今日訂餐 (開團)")
        restaurants_df = db.get_restaurants()
        if not restaurants_df.empty:
            rest_dict = {f"{row['name']} (店號:{row['id']})": row['id'] for _, row in restaurants_df.iterrows()}
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                open_rest = st.selectbox("選擇今日預計訂購的餐廳", list(rest_dict.keys()), key="o_rest")
            with col_t2:
                open_date = st.date_input("點餐日期", datetime.today())
            with col_t3:
                open_time = st.time_input("預計收單時間", datetime.strptime("10:30", "%H:%M").time())
                
            if st.button("🚀 立即發起開團", type="primary", use_container_width=True):
                deadline_str = f"{open_date} {open_time.strftime('%H:%M')}"
                db.create_session(str(open_date), rest_dict[open_rest], deadline_str)
                st.success(f"開團成功！大家現在可以開始去【員工點餐】區點 {open_rest.split(' ')[0]} 囉！")
        else:
            st.warning("⚠️ 目前無任何餐廳資料，請先在下方「新增餐廳」。")

        st.markdown("---")
        st.markdown("### 🏬 餐廳與菜單資料建立")
        
        # 2. 新增與管理常用餐廳
        with st.expander("➕ 新增與管理常用餐廳"):
            c1, c2 = st.columns(2)
            with c1:
                rest_name = st.text_input("餐廳名稱", placeholder="例如：悟饕池上飯包")
            with c2:
                rest_phone = st.text_input("聯絡電話", placeholder="例如：02-23456789")
            if st.button("💾 儲存新增"):
                if rest_name.strip():
                    db.add_restaurant(rest_name.strip(), rest_phone.strip())
                    st.success(f"已新增餐廳：{rest_name}")
                    st.rerun()
                else:
                    st.error("請填寫餐廳名稱")
                    
            st.markdown("---")
            st.write("**🗑️ 刪除誤建餐廳：**")
            all_rests_df = db.get_restaurants()
            if not all_rests_df.empty:
                for _, row in all_rests_df.iterrows():
                    rc_name, rc_phone, rc_action = st.columns([3, 3, 2])
                    rc_name.write(f"🏢 {row['name']}")
                    rc_phone.write(f"📞 {row['phone']}")
                    if rc_action.button("刪除餐廳", key=f"del_rest_{row['id']}"):
                        db.delete_restaurant(row['id'])
                        st.rerun()
            else:
                st.info("目前尚無建立任何餐廳")

        # 3. 管理菜單
        with st.expander("📝 編輯餐廳菜單"):
            if not restaurants_df.empty:
                # Re-fetch dict in case it was updated
                rest_dict = {f"{row['name']} (店號:{row['id']})": row['id'] for _, row in restaurants_df.iterrows()}
                selected_rest = st.selectbox("選擇要編輯菜單的餐廳：", list(rest_dict.keys()))
                rest_id = rest_dict[selected_rest]
                
                st.write(f"**目前 {selected_rest.split(' ')[0]} 的菜單品項：**")
                menu_df = db.get_menu(rest_id)
                if not menu_df.empty:
                    for _, row in menu_df.iterrows():
                        c_name, c_price, c_action = st.columns([4, 2, 2])
                        c_name.write(f"• {row['name']}")
                        c_price.write(f"${row['price']}")
                        if c_action.button("🗑️ 刪除", key=f"del_item_{row['id']}"):
                            db.delete_menu_item(row['id'])
                            st.rerun()
                else:
                    st.info("目前尚無建立任何菜單品項")
                    
                st.markdown("##### 新增品項")
                col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
                with col_m1:
                    item_name = st.text_input("品項名稱", placeholder="例如：香酥大大雞腿飯", key="m_name")
                with col_m2:
                    item_price = st.number_input("價格 (元)", min_value=0, step=5, value=100, key="m_price")
                with col_m3:
                    st.write("")
                    st.write("")
                    if st.button("➕ 新增", use_container_width=True):
                        if item_name and item_price > 0:
                            db.add_menu_item(rest_id, item_name, int(item_price))
                            st.success("新增成功！")
                            st.rerun()
                        else:
                            st.error("請填寫品項名稱與正確數值的價格")
    elif admin_user or admin_pwd:
        st.error("❌ 帳號或密碼錯誤，您沒有權限訪問此頁面！")

elif page == "🍽️ 員工點餐":
    st.header("🍽️ 員工點餐區")
    
    active_sessions = db.get_active_sessions()
    
    if active_sessions.empty:
        st.info("😴 目前沒有正在開放的訂餐活動喔！如有需要請主管開團。")
    else:
        st.success("🎉 目前有正在進行中的訂餐活動！請選擇下方群組並盡速完成點餐。")
        
        session_dict = {}
        for _, row in active_sessions.iterrows():
            label = f"[{row['date']}] {row['restaurant_name']} (收單時間: {row['deadline']})"
            session_dict[label] = row['id']
            
        selected_session_label = st.selectbox("選擇要點餐的團：", list(session_dict.keys()))
        session_id = session_dict[selected_session_label]
        
        session_row = active_sessions[active_sessions['id'] == session_id].iloc[0]
        rest_id = int(session_row['restaurant_id'])
        rest_name = session_row['restaurant_name']
        
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### 🌶️ 今日餐廳：{rest_name}")
        with col_h2:
            st.caption(f"📞 餐廳電話：{session_row['phone']}")
        
        menu_df = db.get_menu(rest_id)
        if menu_df.empty:
            st.warning("⚠️ 這家餐廳目前沒有被輸入任何菜單品項，無法點餐。請洽發起人確認是否有漏填或是選錯餐廳開團喔！")
        else:
            st.markdown("#### 📖 今日菜單一覽")
            st.dataframe(
                menu_df[['name', 'price']].rename(columns={"name": "餐點品項", "price":"價格(元)"}), 
                hide_index=True, 
                use_container_width=True
            )
            
            with st.form("order_form", clear_on_submit=True):
                st.write("#### 📝 填寫您的訂單")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    user_name = st.text_input("🙋 您的姓名/稱呼 (必填)", placeholder="例如：王大明")
                with col_f2:
                    # 菜單產生字典
                    menu_dict = {f"{row['name']} (${row['price']})": row['id'] for _, row in menu_df.iterrows()}
                    selected_item_label = st.selectbox("🍱 選擇餐點", list(menu_dict.keys()))
                    item_id = menu_dict[selected_item_label]
                
                col_f3, col_f4 = st.columns([1, 3])
                with col_f3:
                    quantity = st.number_input("數量", min_value=1, max_value=20, value=1)
                with col_f4:
                    note = st.text_input("備註 (可留空)", placeholder="例如：飯少、不要蔥、小辣")
                
                submit = st.form_submit_button("🛒 送出訂單", type="primary")
                if submit:
                    if not user_name.strip():
                        st.error("請輸入姓名，以便統計時讓主辦人知道！")
                    else:
                        db.place_order(session_id, user_name.strip(), item_id, quantity, note)
                        st.balloons()
                        st.success(f"感謝 {user_name.strip()}，您的訂單已成功送出！")
                        
        st.markdown("---")
        st.write("#### 👀 看看大家點了什麼")
        orders_df = db.get_orders_for_session(session_id)
        if not orders_df.empty:
            show_df = orders_df[['user_name', 'item_name', 'price', 'quantity', 'total_price', 'note']]
            show_df.columns = ["訂購人", "餐點", "單價", "數量", "合計金額", "備註"]
            st.dataframe(show_df, use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無人點餐，趕快當第一個吧！")

elif page == "📊 訂單總覽與結帳":
    st.header("📊 訂單總覽與結帳戰情板")
    
    # 🔒 管理員帳密驗證
    st.info("💡 請輸入管理員或結帳人帳號與密碼解鎖權限。")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        admin_user = st.text_input("👤 管理員帳號：", key="user_checkout")
    with col_c2:
        admin_pwd = st.text_input("🔒 管理員密碼：", type="password", key="pwd_checkout")
    
    if db.verify_admin(admin_user, admin_pwd):
        st.success("✅ 身分驗證成功，已解鎖戰情板與核銷權限！")
        
        conn = db.get_connection()
        all_sessions = pd.read_sql_query('''
            SELECT s.id, s.date, s.is_active, r.name as restaurant_name 
            FROM sessions s JOIN restaurants r ON s.restaurant_id = r.id ORDER BY s.id DESC
        ''', conn)
        conn.close()
        
        if all_sessions.empty:
             st.info("系統中尚無任何揪團或訂單紀錄！")
        else:
            # Create labels
            sess_labels = [f"{'🟢 [進行中]' if row['is_active'] else '🔒 [已結單]'} {row['date']} - {row['restaurant_name']} (ID:{row['id']})" for _, row in all_sessions.iterrows()]
            selected_sess_label = st.selectbox("選擇要檢視或結帳的批次：", sess_labels)
            
            # 萃取 Session ID
            s_id = int(re.search(r'\(ID:(\d+)\)', selected_sess_label).group(1))
            is_active = "進行中" in selected_sess_label
            
            col_admin1, col_admin2 = st.columns([1, 1])
            with col_admin1:
                if is_active:
                     if st.button("🔒 立即截止收單 (員工將無法再加點)", type="primary", use_container_width=True):
                         db.close_session(s_id)
                         st.toast("已截止收單！", icon="✅")
                         st.rerun()
            with col_admin2:
                if st.button("🗑️ 刪除整筆揪團紀錄", use_container_width=True):
                     db.delete_session(s_id)
                     st.success("該筆揪團紀錄及所有相關訂單已徹底刪除！")
                     st.rerun()
                     
            orders_df = db.get_orders_for_session(s_id)
            
            if orders_df.empty:
                st.warning("此團目前還沒有任何人提交訂單。")
            else:
                st.markdown("---")
                col_sum, col_detail = st.columns([1, 2], gap="large")
                
                with col_sum:
                    st.markdown("### 📞 給餐廳的點餐重點")
                    st.caption("這是幫你加總好的清單，打電話過去照著念就可以囉！")
                    # 依品項加總
                    summary_df = orders_df.groupby('item_name')['quantity'].sum().reset_index()
                    summary_df.columns = ["餐點名稱", "需要總數量"]
                    st.dataframe(summary_df, hide_index=True, use_container_width=True)
                    
                    total_cost = orders_df['total_price'].sum()
                    st.markdown(f"## 💰 應付總額：**${total_cost}**")

                with col_detail:
                    st.markdown("### 🧾 收錢明細與狀態")
                    st.caption("點擊按鈕直接切換付款狀態")
                    
                    # 為了避免 Streamlit 的 rerun 機制導致按鈕狀態遺失，我們用 columns 來排版
                    # 每一個列顯示一個人的訂單
                    for _, row in orders_df.iterrows():
                        paid_status = "✅ 已付" if row['has_paid'] else "❌ 未付"
                        
                        c1, c2, c3 = st.columns([5, 2, 2])
                        with c1:
                            note_str = f" `<備註: {row['note']}>`" if str(row['note']) and str(row['note']) != 'None' and row['note'].strip() else ""
                            st.markdown(f"**{row['user_name']}** - {row['item_name']} x{row['quantity']} {note_str}")
                        with c2:
                            st.markdown(f"金額：<span style='color:#3b82f6; font-weight:bold;'>${row['total_price']}</span>", unsafe_allow_html=True)
                        with c3:
                            # Key 必須是 unique 的，所以加上 session_id 跟 order_id
                            if st.button(f"{paid_status}", key=f"pay_{s_id}_{row['id']}"):
                                db.toggle_payment_status(row['id'], row['has_paid'])
                                st.rerun()
                                
                    st.markdown("<hr>", unsafe_allow_html=True)
                    paid_total = orders_df[orders_df['has_paid']==1]['total_price'].sum()
                    unpaid_total = orders_df[orders_df['has_paid']==0]['total_price'].sum()
                    st.write(f"🟢 已收：${paid_total} / 🔴 未收：${unpaid_total}")
    elif admin_user or admin_pwd:
        st.error("❌ 帳號或密碼錯誤，您沒有權限訪問此頁面！")
