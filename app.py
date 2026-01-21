import streamlit as st
import google.generativeai as genai
import twstock
import requests
import json
import time

# --- 頁面基本設定 ---
st.set_page_config(page_title="AI 股市全方位分析", page_icon="📈", layout="wide")

# --- 側邊欄：API Key 設定 ---
with st.sidebar:
    st.header("⚙️ 系統核心設定")
    
    st.markdown("### 1. AI 模型 (Gemini)")
    gemini_key = st.text_input("Gemini API Key", type="password", key="gemini_key")
    st.markdown("[👉 取得免費 Gemini Key](https://aistudio.google.com/app/apikey)")
    
    st.markdown("### 2. 搜尋引擎 (Serper)")
    serper_key = st.text_input("Serper API Key", type="password", key="serper_key")
    st.markdown("[👉 取得免費 Serper Key](https://serper.dev/)")
    st.caption("ℹ️ Serper 是 Google 搜尋的 API 版，註冊即送 2500 次搜尋，能徹底解決雲端部署時被 Google/Yahoo 封鎖的問題。")

# --- 功能 1: 股票代號識別 (結合 twstock) ---
def resolve_stock_id(ticker_input, market):
    ticker = ticker_input.strip().upper()
    name = ticker # 預設名稱為代號本身
    
    if market == "台灣 (TW)":
        # 使用 twstock 本地資料庫查詢，不用連網，速度快且準確
        if ticker in twstock.codes:
            stock_info = twstock.codes[ticker]
            name = stock_info.name
            st.toast(f"✅ 成功辨識：{ticker} 是 {name}", icon="🇹🇼")
            return ticker, name
        else:
            st.toast(f"⚠️ 本地庫找不到 {ticker}，嘗試直接搜尋", icon="🔎")
            return ticker, ticker
    else:
        # 美股直接回傳
        return ticker, ticker

# --- 功能 2: 使用 Serper API 進行穩定搜尋 ---
def search_news_serper(query, api_key):
    url = "https://google.serper.dev/search"
    
    # 針對台灣或美國市場調整搜尋參數
    if "新聞" in query:
        gl = "tw"   # 地區：台灣
        hl = "zh-tw" # 語言：繁中
    else:
        gl = "us"
        hl = "en"

    payload = json.dumps({
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": 5,        # 抓取前 5 筆
        "tbs": "qdr:w"   # 時間限制：過去一週 (qdr:w) 確保資料新鮮
    })
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API 狀態碼錯誤: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# --- 功能 3: Gemini AI 分析 ---
def analyze_stock_data(news_json, ticker, name):
    # 1. 整理搜尋結果
    organic_results = news_json.get("organic", [])
    if not organic_results:
        return "⚠️ 搜尋成功但無相關新聞資料，請嘗試更換關鍵字。", ""

    news_text = ""
    for i, res in enumerate(organic_results, 1):
        title = res.get("title", "無標題")
        snippet = res.get("snippet", "無摘要")
        link = res.get("link", "#")
        date_info = res.get("date", "近期")
        news_text += f"{i}. [{date_info}] {title}\n   摘要: {snippet}\n   連結: {link}\n\n"

    # 2. 設定 AI (改用 gemini-pro 以避免版本錯誤)
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    你是一位華爾街資深操盤手。請根據以下【過去一週的最新網路搜尋資料】，分析「{name} ({ticker})」的投資價值。
    
    【搜尋資料彙整】：
    {news_text}
    
    請以**繁體中文**撰寫一份簡潔有力的投資報告：
    1. **🔥 市場焦點**：用條列式說明最近大家都在討論這家公司的什麼事（營收、產品、醜聞、外資動向...）？
    2. **⚖️ 多空分析**：
       - ✅ 利多：列出 2-3 點看漲理由。
       - 🔻 利空：列出 2-3 點看跌風險。
    3. **🎯 投資建議**：
       - 給予評級：(強力買進 / 分批佈局 / 觀望 / 賣出)
       - 簡述理由。
    
    (請注意：若資料中沒有明確資訊，請誠實告知「目前無相關重大消息」，不要編造數據。)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text, news_text
    except Exception as e:
        return f"AI 分析發生錯誤: {e}", news_text

# --- 主畫面 UI ---
st.title("🤖 AI 股市投資助手 (穩定版)")
st.markdown("""
本系統結合 **Twstock** (台股辨識) 與 **Serper** (Google 搜尋 API)，解決雲端部署時「找不到股票」或「被搜尋引擎封鎖」的問題。
""")

col1, col2 = st.columns([1, 1])
with col1:
    ticker_input = st.text_input("輸入股票代號", placeholder="例如: 2330, 2603, NVDA")
with col2:
    market_select = st.selectbox("選擇市場", ["台灣 (TW)", "美國 (US)"])

if st.button("🚀 開始智能分析", type="primary"):
    # 檢查 API Key
    if not gemini_key:
        st.error("❌ 錯誤：請先在左側輸入 Gemini API Key")
    elif not serper_key:
        st.error("❌ 錯誤：請先在左側輸入 Serper API Key (用於搜尋新聞)")
    elif not ticker_input:
        st.warning("⚠️ 請輸入股票代號")
    else:
        # --- 步驟 1: 辨識股票 ---
        real_ticker, real_name = resolve_stock_id(ticker_input, market_select)
        
        # --- 步驟 2: 構建搜尋關鍵字 ---
        if market_select == "台灣 (TW)":
            query = f"{real_name} {real_ticker} 股價 新聞 營收" # 範例: 聯電 2303 股價 新聞 營收
        else:
            query = f"{real_ticker} stock news analysis forecast"
            
        st.info(f"🔎 正在透過 Google 搜尋： `{query}` ...")
        
        # --- 步驟 3: 執行搜尋 ---
        search_result = search_news_serper(query, serper_key)
        
        # 檢查搜尋結果
        if "error" in search_result:
            st.error(f"搜尋 API 錯誤: {search_result['error']}")
        elif not search_result.get("organic"):
            st.warning("⚠️ 搜尋回傳空值，可能是該公司過於冷門或關鍵字無匹配結果。")
        else:
            # --- 步驟 4: AI 生成報告 ---
            with st.spinner("🧠 AI 正在閱讀新聞並撰寫報告..."):
                analysis_report, raw_news = analyze_stock_data(search_result, real_ticker, real_name)
            
            # --- 顯示結果 ---
            st.success("✅ 分析完成！")
            
            tab_report, tab_raw = st.tabs(["📊 投資分析報告", "📄 原始新聞來源"])
            
            with tab_report:
                st.markdown(analysis_report)
                
            with tab_raw:
                st.text(raw_news)
                with st.expander("查看 API 原始 JSON"):
                    st.json(search_result)
