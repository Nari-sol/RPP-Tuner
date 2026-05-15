import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

# --- ページ設定 ---
st.set_page_config(page_title="RPP Tuner", layout="wide")

# --- 関数: CSV読み込み（文字コード・カンマ対策・複数結合） ---
import re

# --- 関数: CSV読み込み（動的ヘッダー検知・対象月生成） ---
# --- 関数: CSV/Excel読み込み（マルチシート・月情報自動取得） ---
# --- 関数: CSV読み込み（旧：シンプル版） ---
def load_multiple_csvs_basic(uploaded_files):
    combined_df = pd.DataFrame()
    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        success = False
        error_details = []
        
        for skip in [8, 6, 0]:
            if success:
                break
            for encoding in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
                try:
                    decoded_content = content.decode(encoding, errors='replace')
                    
                    df = pd.read_csv(
                        StringIO(decoded_content), 
                        skiprows=skip, 
                        thousands=',',
                        on_bad_lines='skip'
                    )
                    
                    df.columns = df.columns.str.strip()
                    
                    if '実績額(合計)' in df.columns:
                        if not df.empty:
                            combined_df = pd.concat([combined_df, df], ignore_index=True)
                        success = True
                        break
                except Exception as e:
                    error_details.append(f"行スキップ{skip} / {encoding}: {e}")
                    continue
        
        if not success:
            st.error(f"【エラー】ファイル「{uploaded_file.name}」の読み込みに失敗しました。")
            with st.expander("詳細なエラー内容"):
                for err in error_details:
                    st.write(err)
            
    return combined_df

# --- 関数: CSV/Excel読み込み（新：高機能版） ---
def load_multiple_csvs_advanced(uploaded_files):
    combined_df = pd.DataFrame()
    for uploaded_file in uploaded_files:
        success = False
        error_details = []
        
        # ファイル名から月情報を抽出（例：「10月.csv」）
        filename_month = None
        match = re.search(r'(\d+)月', uploaded_file.name)
        if match:
            filename_month = match.group(1) + "月"

        is_excel = uploaded_file.name.endswith(('.xlsx', '.xls', '.xlsm'))
        
        if is_excel:
            try:
                # Excelの場合は全シートを読み込む
                xls = pd.read_excel(uploaded_file, sheet_name=None, header=None)
                for sheet_name, df_raw in xls.items():
                    # 各シートに対してヘッダー特定
                    header_row_idx = -1
                    for i, row in df_raw.iterrows():
                        row_str = row.astype(str).tolist()
                        if any('実績額(合計)' in s or '実績額' in s for s in row_str):
                            header_row_idx = i
                            break
                    
                    if header_row_idx != -1:
                        df = df_raw.iloc[header_row_idx + 1:].copy()
                        df.columns = df_raw.iloc[header_row_idx].astype(str).str.strip()
                        df = df.reset_index(drop=True)
                        
                        # シート名を「対象月」として強制付与
                        df['対象月'] = sheet_name
                        
                        # カラム名の正規化
                        alias_map = {
                            '実績額(合計)': ['実績額(合計)', '実績額', 'コスト', '広告費', '割引後実績額'],
                            '売上金額(合計720時間)': ['売上金額(合計720時間)', '売上金額', '売上', '売上高'],
                            '売上金額(新規720時間)': ['売上金額(新規720時間)', '売上金額(新規)', '新規売上'],
                            '売上金額(既存720時間)': ['売上金額(既存720時間)', '売上金額(既存)', '既存売上'],
                            '売上件数(新規720時間)': ['売上件数(新規720時間)', '新規件数', '新規注文数'],
                            '実績額(新規720時間)': ['実績額(新規720時間)', '実績額(新規)', '新規コスト'],
                            '実績額(既存720時間)': ['実績額(既存720時間)', '実績額(既存)', '既存コスト'],
                            'クリック数(合計)': ['クリック数(合計)', 'クリック数'],
                            'CPC実績(合計)': ['CPC実績(合計)', 'CPC'],
                            'CVR(合計720時間)(%)': ['CVR(合計720時間)(%)', 'CVR', '転換率'],
                            'ROAS(合計720時間)(%)': ['ROAS(合計720時間)(%)', 'ROAS', '総ROAS'],
                            'ROAS(新規720時間)(%)': ['ROAS(新規720時間)(%)', '新規ROAS'],
                            'ROAS(既存720時間)(%)': ['ROAS(既存720時間)(%)', '既存ROAS'],
                            '注文獲得単価(新規720時間)': ['注文獲得単価(新規720時間)', '新規獲得単価', '新規CPA']
                        }
                        for target, aliases in alias_map.items():
                            for alias in aliases:
                                if alias in df.columns:
                                    df[target] = df[alias]
                                    break
                        
                        if not df.empty:
                            combined_df = pd.concat([combined_df, df], ignore_index=True)
                            success = True
            except Exception as e:
                error_details.append(f"Excel ({uploaded_file.name}): {e}")
        else:
            # CSVの場合はエンコーディングを試行
            for encoding in ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']:
                if success: break
                try:
                    uploaded_file.seek(0)
                    content = uploaded_file.getvalue().decode(encoding, errors='replace')
                    df_raw = pd.read_csv(StringIO(content), header=None, on_bad_lines='skip')
                    
                    header_row_idx = -1
                    for i, row in df_raw.iterrows():
                        row_str = row.astype(str).tolist()
                        if any('実績額(合計)' in s or '実績額' in s for s in row_str):
                            header_row_idx = i
                            break
                    
                    if header_row_idx != -1:
                        df = df_raw.iloc[header_row_idx + 1:].copy()
                        df.columns = df_raw.iloc[header_row_idx].astype(str).str.strip()
                        df = df.reset_index(drop=True)
                        
                        # ファイル名から抽出した月を「対象月」として付与
                        if filename_month:
                            df['対象月'] = filename_month
                        
                        alias_map = {
                            '実績額(合計)': ['実績額(合計)', '実績額', 'コスト', '広告費', '割引後実績額'],
                            '売上金額(合計720時間)': ['売上金額(合計720時間)', '売上金額', '売上', '売上高'],
                            '売上金額(新規720時間)': ['売上金額(新規720時間)', '売上金額(新規)', '新規売上'],
                            '売上金額(既存720時間)': ['売上金額(既存720時間)', '売上金額(既存)', '既存売上'],
                            '売上件数(新規720時間)': ['売上件数(新規720時間)', '新規件数', '新規注文数'],
                            '実績額(新規720時間)': ['実績額(新規720時間)', '実績額(新規)', '新規コスト'],
                            '実績額(既存720時間)': ['実績額(既存720時間)', '実績額(既存)', '既存コスト'],
                            'クリック数(合計)': ['クリック数(合計)', 'クリック数'],
                            'CPC実績(合計)': ['CPC実績(合計)', 'CPC'],
                            'CVR(合計720時間)(%)': ['CVR(合計720時間)(%)', 'CVR', '転換率'],
                            'ROAS(合計720時間)(%)': ['ROAS(合計720時間)(%)', 'ROAS', '総ROAS'],
                            'ROAS(新規720時間)(%)': ['ROAS(新規720時間)(%)', '新規ROAS'],
                            'ROAS(既存720時間)(%)': ['ROAS(既存720時間)(%)', '既存ROAS'],
                            '注文獲得単価(新規720時間)': ['注文獲得単価(新規720時間)', '新規獲得単価', '新規CPA']
                        }
                        for target, aliases in alias_map.items():
                            for alias in aliases:
                                if alias in df.columns:
                                    df[target] = df[alias]
                                    break
                        
                        if not df.empty:
                            combined_df = pd.concat([combined_df, df], ignore_index=True)
                            success = True
                            break
                except Exception as e:
                    error_details.append(f"CSV ({encoding}): {e}")
                    continue
        
        if not success:
            st.error(f"【エラー】ファイル「{uploaded_file.name}」から有効なデータ（実績額(合計)）が見つかりませんでした。")
            with st.expander("詳細なエラー内容"):
                for err in error_details:
                    st.write(err)
            
    return combined_df


# --- 関数: ダウンロード用CSVの変換（Excel文字化け対策） ---
@st.cache_data
def convert_df(_df):
    return _df.to_csv(index=False).encode('utf-8-sig')

# --- サイドバー: ナビゲーション ---
# 以下の2行を削除またはコメントアウトします
# st.sidebar.title("RPP Tuner")
# st.sidebar.caption("RPP広告最適化")

# 代わりに以下のコードを追加して、デザインされたタイトルを表示します
st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #FF4B4B 0%, #FF8F8F 100%); border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 32px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            RPP Tuner
        </h1>
        <p style="color: white; margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">
            広告最適化ダッシュボード
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

mode = st.sidebar.radio("表示画面を選択", ["全体ダッシュボード", "商品別分析", "キーワード別分析", "効果検証（Before/After）"])

# --- 【1】全体ダッシュボード画面 ---
# --- 【1】全体ダッシュボード画面 ---
if mode == "全体ダッシュボード":
    st.title("📊 店舗全体パフォーマンス")
    st.write("「すべての広告」レポートをアップロードしてください。")
    
    files = st.file_uploader("すべての広告レポート (CSV / Excel)", accept_multiple_files=True, type=["csv", "xlsx", "xls"])
    
    if files:
        df_total = load_multiple_csvs_advanced(files)
        
        # 変数の初期化
        sum_cost_total = sum_cost_new = sum_cost_existing = 0
        sum_sales_total = sum_sales_new = sum_sales_existing = 0
        sum_orders_new = 0
        calc_roas_total = calc_roas_new = calc_roas_existing = calc_cpa_new = 0

        if not df_total.empty:
            # 数値変換の共通処理
            target_cols = [
                '実績額(合計)', '実績額(新規720時間)', '実績額(既存720時間)',
                '売上金額(合計720時間)', '売上金額(新規720時間)', '売上金額(既存720時間)',
                '売上件数(合計720時間)', '売上件数(新規720時間)', '売上件数(既存720時間)',
                'クリック数(合計)', 'CPC実績(合計)', 'CVR(合計720時間)(%)'
            ]
            for col in target_cols:
                if col in df_total.columns:
                    # 強力なクレンジング：数字とピリオド以外をすべて削除
                    df_total[col] = (
                        df_total[col].astype(str)
                        .str.replace(r'[^\d.]', '', regex=True)
                        .str.strip()
                    )
                    # 数値変換。変換不能なものはNaNになり、それを0で埋める
                    df_total[col] = pd.to_numeric(df_total[col], errors='coerce').fillna(0)

            # --- 月別選択 & 予算設定 UI ---
            st.markdown("---")
            if '対象月' not in df_total.columns:
                df_total['対象月'] = "不明"

            available_months = sorted(df_total['対象月'].dropna().unique(), 
                                      key=lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0,
                                      reverse=True)
            
            c_ui1, c_ui2 = st.columns(2)
            with c_ui1:
                if available_months:
                    selected_month = st.selectbox("📅 表示対象月を選択", options=available_months)
                    df_display = df_total[df_total['対象月'] == selected_month].copy()
                else:
                    selected_month = "不明"
                    df_display = df_total.copy()
            with c_ui2:
                target_budget = st.number_input("🎯 月間目標予算 (広告費)", value=100000, step=10000, format="%d")

            # データ件数チェック
            if len(df_display) == 0:
                st.warning("対象月のデータが0件です。フィルターの条件またはファイル内容を確認してください。")



            # --- 各項目の合計値を算出 ---
            if '実績額(合計)' in df_display.columns:
                sum_cost_total = df_display['実績額(合計)'].sum()
                sum_cost_new = df_display['実績額(新規720時間)'].sum() if '実績額(新規720時間)' in df_display.columns else 0
                sum_cost_existing = df_display['実績額(既存720時間)'].sum() if '実績額(既存720時間)' in df_display.columns else 0
                
                sum_sales_total = df_display['売上金額(合計720時間)'].sum()
                sum_sales_new = df_display['売上金額(新規720時間)'].sum() if '売上金額(新規720時間)' in df_display.columns else 0
                sum_sales_existing = df_display['売上金額(既存720時間)'].sum() if '売上金額(既存720時間)' in df_display.columns else 0
                
                sum_orders_total = df_display['売上件数(合計720時間)'].sum() if '売上件数(合計720時間)' in df_display.columns else 0
                sum_orders_new = df_display['売上件数(新規720時間)'].sum() if '売上件数(新規720時間)' in df_display.columns else 0
                if '売上件数(既存720時間)' in df_display.columns:
                    sum_orders_existing = df_display['売上件数(既存720時間)'].sum()
                else:
                    sum_orders_existing = sum_orders_total - sum_orders_new
                
                sum_clicks_total = df_display['クリック数(合計)'].sum() if 'クリック数(合計)' in df_display.columns else 0

                # --- 着地予測の計算ロジック ---
                date_col = None
                for col in ['日付', '対象日', '期間', '年月日']:
                    if col in df_display.columns:
                        date_col = col
                        break
                
                import datetime
                now = datetime.datetime.now()
                month_match = re.search(r'(\d+)', str(selected_month))
                if month_match:
                    target_month_num = int(month_match.group(1))
                    if target_month_num in [4, 6, 9, 11]: total_days = 30
                    elif target_month_num == 2:
                        year = now.year
                        total_days = 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28
                    else: total_days = 31
                else:
                    total_days = 30
                
                # 経過日数の判定（ユニークな日付数、なければ1日とする）
                days_passed = df_display[date_col].nunique() if date_col else 1
                if days_passed <= 0: days_passed = 1
                
                proj_cost = (sum_cost_total / days_passed) * total_days
                proj_sales = (sum_sales_total / days_passed) * total_days
                progress_rate = (sum_cost_total / target_budget * 100) if target_budget > 0 else 0

                # --- 要件：予算進捗・着地予測の表示 ---
                st.subheader("📊 予算進捗・着地予測")
                c_prog1, c_prog2 = st.columns([1, 1.5])
                
                with c_prog1:
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number+delta",
                        value = sum_cost_total,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "予算消化状況", 'font': {'size': 16, 'color': 'white'}},
                        delta = {'reference': target_budget, 'increasing': {'color': "#FF4B4B"}},
                        gauge = {
                            'axis': {'range': [None, max(target_budget, sum_cost_total) * 1.2], 'tickwidth': 1, 'tickcolor': "white"},
                            'bar': {'color': "#FF8F8F"},
                            'bgcolor': "rgba(0,0,0,0)",
                            'borderwidth': 2,
                            'bordercolor': "gray",
                            'steps': [
                                {'range': [0, target_budget], 'color': 'rgba(255, 255, 255, 0.1)'},
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': target_budget
                            }
                        }
                    ))
                    fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=280, margin=dict(l=20, r=20, t=70, b=20))
                    st.plotly_chart(fig_gauge, use_container_width=True)

                with c_prog2:
                    st.write("") # 上部マージン
                    st.write("")
                    p1, p2 = st.columns(2)
                    p1.metric("予想着地コスト", f"{int(proj_cost):,}円", 
                              f"{int(proj_cost - target_budget):,}円" if target_budget > 0 else None, 
                              delta_color="inverse")
                    p2.metric("予想着地売上", f"{int(proj_sales):,}円", f"進捗率: {progress_rate:.1f}%")
                    
                    st.info(f"💡 {selected_month} のデータ（{days_passed}日間）に基づき、月末（{total_days}日間）を予測しています。")

                # --- KPI表示 ---
                st.subheader("🎯 主要パフォーマンス指標")
                
                # 2. 指標を自前で計算（0除算対策）
                # ※実績額(新規)や(既存)がない場合は、全体のコストを使って比率を見るか、0を表示
                calc_roas_total = (sum_sales_total / sum_cost_total * 100) if sum_cost_total > 0 else 0
                
                # 新規ROAS: 新規売上 / (新規コストがあればそれを使う、なければ全体コスト)
                divisor_new = sum_cost_new if sum_cost_new > 0 else sum_cost_total
                calc_roas_new = (sum_sales_new / divisor_new * 100) if divisor_new > 0 else 0
                
                # 既存ROAS: 既存売上 / (既存コストがあればそれを使う、なければ全体コスト)
                divisor_existing = sum_cost_existing if sum_cost_existing > 0 else sum_cost_total
                calc_roas_existing = (sum_sales_existing / divisor_existing * 100) if divisor_existing > 0 else 0
                
                # 全体CPA: 全体コスト / 全体注文数
                calc_cpa_total = (sum_cost_total / sum_orders_total) if sum_orders_total > 0 else 0
                
                # 新規獲得単価: (新規コストがあればそれ、なければ全体) / 新規注文数
                calc_cpa_new = (divisor_new / sum_orders_new) if sum_orders_new > 0 else 0
                
                # 既存CPA: (既存コストがあればそれ、なければ全体) / 既存注文数
                calc_cpa_existing = (divisor_existing / sum_orders_existing) if sum_orders_existing > 0 else 0
                
                # --- CVR計算 ---
                calc_cvr_total = (sum_orders_total / sum_clicks_total * 100) if sum_clicks_total > 0 else 0
                
                # 新規・既存クリック数の推定（コスト比率で按分）
                if sum_cost_total > 0:
                    new_click_ratio = sum_cost_new / sum_cost_total
                    exist_click_ratio = sum_cost_existing / sum_cost_total
                else:
                    new_click_ratio = 0
                    exist_click_ratio = 0
                    
                est_clicks_new = sum_clicks_total * new_click_ratio
                est_clicks_existing = sum_clicks_total * exist_click_ratio
                
                calc_cvr_new = (sum_orders_new / est_clicks_new * 100) if est_clicks_new > 0 else 0
                calc_cvr_existing = (sum_orders_existing / est_clicks_existing * 100) if est_clicks_existing > 0 else 0
                
                # --- CPC計算 ---
                calc_cpc_total = (sum_cost_total / sum_clicks_total) if sum_clicks_total > 0 else 0
                calc_cpc_new = (divisor_new / est_clicks_new) if est_clicks_new > 0 else 0
                calc_cpc_existing = (divisor_existing / est_clicks_existing) if est_clicks_existing > 0 else 0

                # --- 客単価 (AOV) 計算 ---
                calc_aov_total = (sum_sales_total / sum_orders_total) if sum_orders_total > 0 else 0
                calc_aov_new = (sum_sales_new / sum_orders_new) if sum_orders_new > 0 else 0
                calc_aov_existing = (sum_sales_existing / sum_orders_existing) if sum_orders_existing > 0 else 0

                # --- 新規顧客比率計算 ---
                calc_new_ratio_sales = (sum_sales_new / sum_sales_total * 100) if sum_sales_total > 0 else 0
                calc_new_ratio_orders = (sum_orders_new / sum_orders_total * 100) if sum_orders_total > 0 else 0
                
                # 3. フォーマット表示
                r1, r2, r3 = st.columns(3)
                r1.metric("総ROAS (720h)", f"{calc_roas_total:,.1f}%")
                r2.metric("新規ROAS (720h)", f"{calc_roas_new:,.1f}%")
                r3.metric("既存ROAS (720h)", f"{calc_roas_existing:,.1f}%")
                
                st.write("") # 上下の間隔調整
                c1, c2, c3 = st.columns(3)
                c1.metric("総CPA", f"{int(calc_cpa_total):,}円")
                c2.metric("新規CPA", f"{int(calc_cpa_new):,}円")
                c3.metric("既存CPA", f"{int(calc_cpa_existing):,}円")
                
                st.write("") # 上下の間隔調整
                v1, v2, v3 = st.columns(3)
                v1.metric("総CVR", f"{calc_cvr_total:,.2f}%")
                v2.metric("新規CVR", f"{calc_cvr_new:,.2f}%")
                v3.metric("既存CVR", f"{calc_cvr_existing:,.2f}%")

                st.write("") # 上下の間隔調整
                p1, p2, p3 = st.columns(3)
                p1.metric("総CPC", f"{int(calc_cpc_total):,}円")
                p2.metric("新規CPC", f"{int(calc_cpc_new):,}円")
                p3.metric("既存CPC", f"{int(calc_cpc_existing):,}円")

                st.write("") # 上下の間隔調整
                a1, a2, a3 = st.columns(3)
                a1.metric("総客単価", f"{int(calc_aov_total):,}円")
                a2.metric("新規客単価", f"{int(calc_aov_new):,}円")
                a3.metric("既存客単価", f"{int(calc_aov_existing):,}円")

                # --- 新規顧客比率の表示 ---
                st.write("") # 上下の間隔調整
                st.markdown("<div style='padding: 15px; background-color: rgba(255, 255, 255, 0.05); border-radius: 8px; border-left: 4px solid #4A90E2;'>", unsafe_allow_html=True)
                st.markdown("#### 🌟 新規顧客の獲得比率", unsafe_allow_html=True)
                n1, n2 = st.columns(2)
                n1.metric("売上ベース", f"{calc_new_ratio_sales:,.1f}%")
                n2.metric("件数ベース", f"{calc_new_ratio_orders:,.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)


                # --- 要件2：新規 vs 既存の構成比 ---
                st.markdown("### 🔄 新規・既存の構成比")
                c1, c2 = st.columns(2)
                with c1:
                    # コスト構成
                    if sum_cost_new + sum_cost_existing > 0:
                        fig_cost_pie = px.pie(values=[sum_cost_new, sum_cost_existing], names=['新規コスト', '既存コスト'], title="コスト構成比", hole=0.4)
                        st.plotly_chart(fig_cost_pie, use_container_width=True)
                    else:
                        st.info("コストの新規・既存内訳データがありません。")
                
                with c2:
                    # 売上構成
                    if sum_sales_new + sum_sales_existing > 0:
                        fig_sales_pie = px.pie(values=[sum_sales_new, sum_sales_existing], names=['新規売上', '既存売上'], title="売上構成比", hole=0.4)
                        st.plotly_chart(fig_sales_pie, use_container_width=True)
                    else:
                        st.info("売上の新規・既存内訳データがありません。")


                # 月次比較
                st.subheader("📈 月次パフォーマンス比較")
                df_monthly = df_total.groupby('対象月')[['実績額(合計)', '売上金額(合計720時間)']].sum().reset_index()
                fig_monthly = go.Figure()
                fig_monthly.add_trace(go.Bar(x=df_monthly['対象月'], y=df_monthly['実績額(合計)'], name='コスト'))
                fig_monthly.add_trace(go.Bar(x=df_monthly['対象月'], y=df_monthly['売上金額(合計720時間)'], name='売上'))
                fig_monthly.update_layout(barmode='group', xaxis_title="対象月", yaxis_title="金額（円）")
                st.plotly_chart(fig_monthly, use_container_width=True)

                # --- 要件4：RPPパフォーマンス・シミュレーター ---
                st.markdown("---")
                
                # デフォルト値の設定 (過去データからのベースライン算出)
                cur_cost = sum_cost_total if sum_cost_total > 0 else 0
                cur_cpc = calc_cpc_total if calc_cpc_total > 0 else 100.0
                cur_cvr_new = calc_cvr_new if calc_cvr_new > 0 else 2.0
                cur_cvr_exist = calc_cvr_existing if calc_cvr_existing > 0 else 2.0
                cur_aov_new = calc_aov_new if calc_aov_new > 0 else 5000.0
                cur_aov_exist = calc_aov_existing if calc_aov_existing > 0 else 5000.0
                cur_new_ratio = calc_new_ratio_orders if calc_new_ratio_orders > 0 else 60.0
                
                # シミュレーター全体のコンテナ
                sim_container = st.container()
                with sim_container:
                    # プレースホルダーを用意
                    header_placeholder = st.empty()
                    chart_placeholder = st.empty()
                    
                    # --- 同期入力UIのための状態初期化 ---
                    def init_sync(name, default_val):
                        num_key = f"num_{name}"
                        sli_key = f"sli_{name}"
                        if num_key not in st.session_state:
                            st.session_state[num_key] = default_val
                        if sli_key not in st.session_state:
                            st.session_state[sli_key] = default_val

                    init_sync('cost', max(0, int(cur_cost)))
                    init_sync('cpc', max(1, int(cur_cpc)))
                    init_sync('cvr_new', max(0.0, float(cur_cvr_new)))
                    init_sync('cvr_exist', max(0.0, float(cur_cvr_exist)))
                    init_sync('aov_new', max(1, int(cur_aov_new)))
                    init_sync('aov_exist', max(1, int(cur_aov_exist)))
                    init_sync('new_ratio', max(0, min(100, int(cur_new_ratio))))

                    def sync_state(source_key, target_key):
                        st.session_state[target_key] = st.session_state[source_key]

                    def draw_synced_input(label, name, min_val, max_val, step):
                        num_key = f"num_{name}"
                        sli_key = f"sli_{name}"
                        st.markdown(f"<div style='font-size:14px; margin-bottom:5px; color:#c0c0c0;'>{label}</div>", unsafe_allow_html=True)
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.slider(
                                label, min_value=min_val, max_value=max_val, step=step, 
                                key=sli_key, on_change=sync_state, args=(sli_key, num_key),
                                label_visibility="collapsed"
                            )
                        with c2:
                            st.number_input(
                                label, min_value=min_val, max_value=max_val, step=step,
                                key=num_key, on_change=sync_state, args=(num_key, sli_key),
                                label_visibility="collapsed"
                            )
                        return st.session_state[num_key]

                    # コントロール部（下部配置・3列にして高さを圧縮）
                    col_in1, col_in2, col_in3 = st.columns(3)
                    with col_in1:
                        sim_cost = draw_synced_input("実績額 (広告費) [円]", 'cost', 0, max(100000, int(cur_cost*2)), 1000)
                        sim_cpc = draw_synced_input("CPC実績 [円]", 'cpc', 1, max(300, int(cur_cpc*2)), 1)
                        sim_new_ratio = draw_synced_input("新規顧客比率 [%]", 'new_ratio', 0, 100, 1)
                    with col_in2:
                        sim_cvr_new = draw_synced_input("新規CVR [%]", 'cvr_new', 0.0, max(20.0, float(round(cur_cvr_new*2, 1))), 0.1)
                        sim_aov_new = draw_synced_input("新規客単価 [円]", 'aov_new', 1000, max(50000, int(cur_aov_new*2)), 500)
                    with col_in3:
                        sim_cvr_exist = draw_synced_input("既存CVR [%]", 'cvr_exist', 0.0, max(20.0, float(round(cur_cvr_exist*2, 1))), 0.1)
                        sim_aov_exist = draw_synced_input("既存客単価 [円]", 'aov_exist', 1000, max(50000, int(cur_aov_exist*2)), 500)

                    if st.button("シミュレーションをリセット", use_container_width=True):
                        for k in ['num_cost', 'sli_cost', 'num_cpc', 'sli_cpc', 'num_cvr_new', 'sli_cvr_new', 'num_cvr_exist', 'sli_cvr_exist', 'num_aov_new', 'sli_aov_new', 'num_aov_exist', 'sli_aov_exist', 'num_new_ratio', 'sli_new_ratio']:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.rerun()

                    # 計算処理
                    sim_clicks = sim_cost / sim_cpc if sim_cpc > 0 else 0
                    new_clicks = sim_clicks * (sim_new_ratio / 100)
                    exist_clicks = sim_clicks - new_clicks
                    
                    new_orders = new_clicks * (sim_cvr_new / 100)
                    exist_orders = exist_clicks * (sim_cvr_exist / 100)
                    sim_orders = new_orders + exist_orders
                    
                    new_sales = new_orders * sim_aov_new
                    exist_sales = exist_orders * sim_aov_exist
                    sim_sales = new_sales + exist_sales
                    
                    new_cost = sim_cost * (sim_new_ratio / 100)
                    exist_cost = sim_cost - new_cost
                    
                    sim_roas = (sim_sales / sim_cost * 100) if sim_cost > 0 else 0
                    new_roas = (new_sales / new_cost * 100) if new_cost > 0 else 0
                    exist_roas = (exist_sales / exist_cost * 100) if exist_cost > 0 else 0
                    
                    # 上部ヘッダー部（動的メトリクス）の描画
                    with header_placeholder.container():
                        hc0, hc1, hc2, hc3, hc4 = st.columns([2, 1, 1, 1, 1])
                        with hc0:
                            st.markdown("### RPP広告シミュレーター")
                        with hc1:
                            st.markdown(f"<div style='font-size:12px;color:gray'>クリック数</div><div style='font-size:18px;font-weight:bold'>{int(sim_clicks):,}回</div>", unsafe_allow_html=True)
                        with hc2:
                            st.markdown(f"<div style='font-size:12px;color:gray'>コンバージョン</div><div style='font-size:18px;font-weight:bold'>{int(sim_orders):,}件</div>", unsafe_allow_html=True)
                        with hc3:
                            st.markdown(f"<div style='font-size:12px;color:gray'>予想売上</div><div style='font-size:18px;font-weight:bold'>¥{int(sim_sales):,}</div>", unsafe_allow_html=True)
                        with hc4:
                            st.markdown(f"<div style='font-size:12px;color:gray'>合計ROAS</div><div style='font-size:18px;font-weight:bold'>{sim_roas:.0f}%</div>", unsafe_allow_html=True)
                    
                    # グラフ部の描画（ダークテーマ）
                    with chart_placeholder.container():
                        st.markdown("<div style='background-color: #1a1c24; padding: 10px 20px; border-radius: 10px; margin-top: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True)
                        
                        # グラフ1: セグメント別 売上構成
                        fig1 = go.Figure()
                        fig1.add_trace(go.Bar(name='新規顧客', x=[''], y=[new_sales], marker_color='#4A90E2', text=f'新規顧客<br>¥{new_sales/10000:.1f}万', textposition='auto', textfont=dict(color='white', size=14)))
                        fig1.add_trace(go.Bar(name='既存顧客', x=[''], y=[exist_sales], marker_color='#90ED7D', text=f'既存顧客<br>¥{exist_sales/10000:.1f}万', textposition='auto', textfont=dict(color='black', size=14)))
                        fig1.update_layout(
                            barmode='stack', 
                            title=dict(text="セグメント別 売上構成 (円)", font=dict(color='white', size=16)),
                            yaxis=dict(title="↑ 金額 (円)", color='white', gridcolor='#333333'),
                            xaxis=dict(color='white', showticklabels=False),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            legend=dict(font=dict(color='white'), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            margin=dict(l=40, r=20, t=50, b=10),
                            height=180
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                        
                        # グラフ2: セグメント別 ROAS比較
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(x=['全体ROAS', '新規顧客', '既存顧客'], y=[sim_roas, new_roas, exist_roas], marker_color=['#A9C2F0', '#4A90E2', '#90ED7D'], text=[f"{sim_roas:.1f}%", f"{new_roas:.1f}%", f"{exist_roas:.1f}%"], textposition='outside', textfont=dict(color='white')))
                        fig2.add_hline(y=100, line_color="white", line_dash="solid")
                        fig2.update_layout(
                            title=dict(text="セグメント別 ROAS比較 (%)", font=dict(color='white', size=16)),
                            yaxis=dict(title="↑ ROAS (%)", range=[0, max(120, max([sim_roas, new_roas, exist_roas, 0])*1.2)], color='white', gridcolor='#333333'),
                            xaxis=dict(color='white'),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            showlegend=False,
                            margin=dict(l=40, r=20, t=40, b=20),
                            height=200
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)


            else:
                st.error("【エラー】実績データが不足しているためダッシュボードを表示できません。")

# --- 【2】商品別・キーワード別分析画面 ---
elif mode in ["商品別分析", "キーワード別分析"]:
    is_keyword = (mode == "キーワード別分析")
    
    if is_keyword:
        st.title("🔑 キーワード別分析")
        st.write("「検索キーワード別」レポートをアップロードしてください。")
        files = st.file_uploader("キーワード別レポート (CSV)", accept_multiple_files=True, type="csv")
    else:
        st.title("📦 商品別分析")
        st.write("「商品別」レポートをアップロードしてください。")
        files = st.file_uploader("商品別レポート (CSV)", accept_multiple_files=True, type="csv")
    
    if files:
        df_raw = load_multiple_csvs_basic(files)
        
        if not df_raw.empty:
            num_cols = ['実績額(合計)', '売上金額(合計720時間)', 'クリック数(合計)', '売上件数(合計720時間)', 'CVR(合計720時間)(%)', 'ROAS(合計720時間)(%)']
            for col in num_cols:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)

            st.sidebar.markdown("---")
            st.sidebar.subheader("🚨 除外・減額のボーダー設定")
            st.sidebar.write("以下の ① か ② を満たし、かつ ③ を下回るものを抽出します。")
            
            profit_threshold = st.sidebar.number_input("① コスト ◯円以上", value=2750, step=250, key="profit_threshold")
            cvr_threshold = st.sidebar.number_input("② または クリック ◯回以上", value=50, step=10, key="cvr_threshold")
            roas_threshold = st.sidebar.number_input("③ かつ ROAS ◯%未満", value=500, step=50, key="roas_threshold")

            cond_cost = df_raw['実績額(合計)'] >= profit_threshold
            cond_clicks = df_raw['クリック数(合計)'] >= cvr_threshold
            cond_roas = df_raw['ROAS(合計720時間)(%)'] < roas_threshold
            
            stop_list = df_raw[(cond_cost | cond_clicks) & cond_roas].copy()
            
            if is_keyword:
                tab_title_1, tab_title_2 = "🔴 除外・減額候補（キーワード）", "🟢 強化候補（キーワード）"
                desc_1 = "無駄なクリックを稼いでいるキーワードです。商品と関係がない場合は「除外設定」を検討してください。"
                desc_2 = "転換率（CVR）が高いキーワードです。さらに露出を増やすための「単価アップ」を検討してください。"
                file_prefix = "keyword"
            else:
                tab_title_1, tab_title_2 = "🔴 止血対象（商品）", "🟢 強化候補（商品）"
                desc_1 = "予算を無駄に消費している商品です。広告の停止や、ページの見直しが必要です。"
                desc_2 = "売れるポテンシャルが高い商品です。露出を強化して売上の最大化を狙いましょう。"
                file_prefix = "product"

            if not stop_list.empty:
                def get_recommended_action(row):
                    actions = []
                    if row['実績額(合計)'] >= profit_threshold:
                        actions.append("広告停止/単価減額")
                    if row['クリック数(合計)'] >= cvr_threshold:
                        if is_keyword:
                            actions.append("KW除外/見直し")
                        else:
                            actions.append("ページ見直し")
                    if len(actions) == 2:
                        return "🚨 " + " ＋ ".join(actions)
                    elif len(actions) == 1:
                        return "💡 " + actions[0]
                    else:
                        return "要確認"
                        
                stop_list['推奨アクション'] = stop_list.apply(get_recommended_action, axis=1)

            tab1, tab2 = st.tabs([tab_title_1, tab_title_2])
            
            with tab1:
                st.subheader(tab_title_1)
                st.error(f"🔍 現在の絞り込み: ( コスト {profit_threshold:,} 円以上 または クリック {cvr_threshold:,} 回以上 ) ＆ ROAS {roas_threshold:,} %未満")
                st.caption(desc_1)
                
                if not stop_list.empty:
                    display_cols = ['商品管理番号', '推奨アクション', '実績額(合計)', 'クリック数(合計)', '売上金額(合計720時間)', '売上件数(合計720時間)', 'ROAS(合計720時間)(%)']
                    if is_keyword and 'キーワード' in df_raw.columns:
                        display_cols.insert(1, 'キーワード')
                    
                    df_stop_display = stop_list[display_cols].sort_values('実績額(合計)', ascending=False)
                    st.dataframe(df_stop_display)
                    
                    csv_stop = convert_df(df_stop_display)
                    st.download_button(
                        label="📥 このリストをCSVでダウンロード",
                        data=csv_stop,
                        file_name=f"stop_list_{file_prefix}.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("対象は見つかりませんでした！")
            
            with tab2:
                st.subheader(tab_title_2)
                st.caption(desc_2)
                avg_cvr = df_raw[df_raw['売上件数(合計720時間)'] > 0]['CVR(合計720時間)(%)'].mean()
                upsell_list = df_raw[(df_raw['CVR(合計720時間)(%)'] > avg_cvr) & (df_raw['売上件数(合計720時間)'] > 0)]
                
                if not upsell_list.empty:
                    display_cols = ['商品管理番号', 'CVR(合計720時間)(%)', '実績額(合計)', '売上金額(合計720時間)', 'ROAS(合計720時間)(%)']
                    if is_keyword and 'キーワード' in df_raw.columns:
                        display_cols.insert(1, 'キーワード')
                    
                    df_upsell_display = upsell_list[display_cols].sort_values('CVR(合計720時間)(%)', ascending=False)
                    st.dataframe(df_upsell_display)
                    
                    csv_upsell = convert_df(df_upsell_display)
                    st.download_button(
                        label="📥 このリストをCSVでダウンロード",
                        data=csv_upsell,
                        file_name=f"upsell_list_{file_prefix}.csv",
                        mime="text/csv"
                    )
                else:
                    st.write("候補がまだ見つかりません。")
        else:
            st.warning("データの読み込みに失敗しました。")


# --- 【3】効果検証（Before/After）画面 ---
elif mode == "効果検証（Before/After）":
    st.title("⚖️ 効果検証（Before / After）")
    st.write("「すべての広告」レポートを使用して、施策前と施策後のパフォーマンスを比較します。")
    
    col_before, col_after = st.columns(2)
    with col_before:
        st.subheader("🔙 Before（チューニング前）")
        files_before = st.file_uploader("過去のレポート (CSV)", accept_multiple_files=True, type="csv", key="file_before")
    with col_after:
        st.subheader("🔜 After（チューニング後）")
        files_after = st.file_uploader("最新のレポート (CSV)", accept_multiple_files=True, type="csv", key="file_after")
        
    if files_before and files_after:
        df_before = load_multiple_csvs_basic(files_before)
        df_after = load_multiple_csvs_basic(files_after)
        
        if not df_before.empty and not df_after.empty:
            cost_b = pd.to_numeric(df_before['実績額(合計)'], errors='coerce').sum()
            sales_b = pd.to_numeric(df_before['売上金額(合計720時間)'], errors='coerce').sum()
            roas_b = (sales_b / cost_b * 100) if cost_b > 0 else 0
            
            cost_a = pd.to_numeric(df_after['実績額(合計)'], errors='coerce').sum()
            sales_a = pd.to_numeric(df_after['売上金額(合計720時間)'], errors='coerce').sum()
            roas_a = (sales_a / cost_a * 100) if cost_a > 0 else 0
            
            cost_diff = cost_a - cost_b
            sales_diff = sales_a - sales_b
            roas_diff = roas_a - roas_b
            
            st.markdown("---")
            st.subheader("🎯 チューニングの成果（Before → After）")
            
            m1, m2, m3 = st.columns(3)
            # コストは下がった方がプラス評価になるため、delta_color="inverse" を指定して緑色にします
            m1.metric("総実績額（コスト）", f"{int(cost_a):,}円", f"{int(cost_diff):,}円", delta_color="inverse")
            m2.metric("総売上金額", f"{int(sales_a):,}円", f"{int(sales_diff):,}円")
            m3.metric("平均ROAS", f"{round(roas_a, 1)}%", f"{round(roas_diff, 1)}%")
            
            if roas_diff > 0:
                st.success("素晴らしい成果です！チューニングによってROASが改善しました。この調子でPDCAを回していきましょう。")
            elif roas_diff <= 0 and sales_diff > 0:
                st.warning("売上の拡大には成功していますが、ROASが低下傾向にあります。コストの消化ペースに注意してください。")
            elif roas_diff <= 0 and sales_diff <= 0:
                st.error("パフォーマンスが悪化しています。除外キーワードの追加や、入札単価の見直しなどの止血対応を急いでください。")
        else:
            st.warning("データの読み込みに失敗しました。正しいCSVファイルか確認してください。")