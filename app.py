import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

# --- ページ設定 ---
st.set_page_config(page_title="RPP Tuner", layout="wide")

# --- 関数: CSV読み込み（文字コード・カンマ対策・複数結合） ---
def load_multiple_csvs(uploaded_files):
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
                    
                    # 変更点: on_bad_lines='skip' を追加して、カンマの数が合わないエラー行を無視します
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
            with st.expander("開発者用：エラーの詳細原因（解決できない場合はここを教えてください）"):
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
if mode == "全体ダッシュボード":
    st.title("📊 店舗全体パフォーマンス")
    st.write("「すべての広告」レポートをアップロードしてください。")
    
    files = st.file_uploader("すべての広告レポート (CSV)", accept_multiple_files=True, type="csv")
    
    if files:
        df_total = load_multiple_csvs(files)
        
        if not df_total.empty:
            date_col_name = None
            for col in ['日付', '対象日', '期間', '年月日']:
                if col in df_total.columns:
                    date_col_name = col
                    break
            
            if date_col_name:
                # 変更点：日本語の「年」「月」「日」を「-」に変換して日付として認識させる
                clean_dates = df_total[date_col_name].astype(str)
                clean_dates = clean_dates.str.replace('年', '-', regex=False)
                clean_dates = clean_dates.str.replace('月', '-', regex=False)
                clean_dates = clean_dates.str.replace('日', '', regex=False)
                clean_dates = clean_dates.str.rstrip('-') # 末尾のハイフンを削除
                
                df_total[date_col_name] = pd.to_datetime(clean_dates, errors='coerce')
                df_total = df_total.dropna(subset=[date_col_name])
                
                if df_total.empty:
                    st.warning(f"「{date_col_name}」列のデータを日付として変換できませんでした。")
                else:
                    df_total = df_total.sort_values(date_col_name)
                    
                    col1, col2, col3 = st.columns(3)
                    cost_sum = pd.to_numeric(df_total['実績額(合計)'], errors='coerce').sum()
                    sales_sum = pd.to_numeric(df_total['売上金額(合計720時間)'], errors='coerce').sum()
                    
                    col1.metric("総実績額", f"{int(cost_sum):,}円")
                    col2.metric("総売上金額", f"{int(sales_sum):,}円")
                    roas_avg = (sales_sum / cost_sum * 100) if cost_sum > 0 else 0
                    col3.metric("平均ROAS", f"{round(roas_avg, 1)}%")
                    
                    st.subheader("推移グラフ")
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Bar(x=df_total[date_col_name], y=df_total['実績額(合計)'], name='コスト'))
                    fig_trend.add_trace(go.Scatter(x=df_total[date_col_name], y=df_total['売上金額(合計720時間)'], name='売上', yaxis='y2'))
                    fig_trend.update_layout(
                        yaxis=dict(title="コスト（円）"),
                        yaxis2=dict(title="売上（円）", overlaying='y', side='right'),
                        legend=dict(x=0, y=1.1, orientation="h")
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                    
                    st.subheader("ROAS推移")
                    df_total['ROAS(合計720時間)(%)'] = pd.to_numeric(df_total['ROAS(合計720時間)(%)'], errors='coerce')
                    fig_roas = px.line(df_total, x=date_col_name, y='ROAS(合計720時間)(%)', markers=True)
                    st.plotly_chart(fig_roas, use_container_width=True)
            else:
                st.warning("データ内に「日付」の列が見つかりませんでした。")
                st.info(f"読み込めた列名: {', '.join(df_total.columns)}")

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
        df_raw = load_multiple_csvs(files)
        
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
        df_before = load_multiple_csvs(files_before)
        df_after = load_multiple_csvs(files_after)
        
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
            
            st.success("日々のチューニングがしっかりと数字に表れていますね！引き続きPDCAを回していきましょう。")
        else:
            st.warning("データの読み込みに失敗しました。正しいCSVファイルか確認してください。")