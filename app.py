import streamlit as st
import google.generativeai as genai
import twstock
import requests
import json

# --- 設定頁面 ---
st.set_page_config(page_title="AI 專業投資助手 (API版)", page_icon="🏦", layout="wide")

# --- 側邊欄：API Key 設定 ---
with st.sidebar:
    st.header("⚙️ 系統金鑰設定")
    
    st.markdown("### 1. 腦袋 (AI)")
    gemini_key = st.text_input("Gemini API Key", type="password", key="gemini")
    st.markdown("[👉 取得 Gemini Key](https://aistudio.google.com/app/apikey)")
    
    st.markdown("### 2. 眼睛 (搜尋)")
    serper_key = st.text_input("Serper API Key", type="password", key="serper")
    st.markdown("[👉 取得 Serper Key (Google搜尋)](https://serper.dev/)")
    st.caption("註冊 Serper 即送 2500 次免費搜尋，解決雲端被擋問題。")

# --- 核心 1: 透過 twstock 識別台股 ---
def get_stock_identity(ticker, country):
    ticker = ticker.strip().upper()
    name = ticker
    
    if country == "台灣 (TW)":
        # 1. 先查 twstock 本地庫 (最快最穩)
        if ticker in twstock.codes:
            name = twstock.codes[ticker].name
            st.success(f"✅ 代號識別成功：{ticker} -> {name}")
            return ticker, name
        else:
            st.warning(f"⚠️ 本地庫未收錄 {ticker}，將直接使用代號搜尋。")
            return ticker, ticker
    else:
        # 美股直接回傳
        return ticker, ticker

# --- 核心 2: 使用 Serper API 搜尋 (穩定不被擋) ---
def search_google_serper(query, api_key):
    url = "https://google.serper.dev/search"
    
    # 根據查詢內容決定搜尋地區
    gl = "tw" if "新聞" in query or "營收" in query else "us"
    hl = "zh-tw" if gl == "tw" else "en"

    payload = json.dumps({
        "q": query,
        "gl": gl,       # 地區: 台灣
        "hl": hl,       # 語言: 繁中
        "num": 5,       # 搜尋結果條數
        "tbs": "qdr:w"  # 限制時間：過去一週 (qdr:w) 或 過去一個月 (qdr:m)
    })
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# --- 核心 3: 資料整理與 AI 分析 ---
def analyze_market(search_json, ticker, name):
    # 整理 Serper 回傳的 JSON 資料
    organic_results = search_json.get("organic", [])
    if not organic_results:
        return "⚠️ 搜尋 API 回傳成功，但在指定時間內找不到相關新聞。"

    news_text = ""
    for idx, result in enumerate(organic_results, 1):
        title = result.get("title", "無標題")
        snippet = result.get("snippet", "無摘要")
        link = result.get("link", "#")
        date = result.get("date", "近期")
        news_text += f"{idx}. [{date}] {title}\n   摘要: {snippet}\n   連結: {link}\n\n"

    # 呼叫 Gemini
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位華爾街資深分析師。請根據以下【Google 最新搜尋結果】，分析「{name} ({ticker})」的投資價值。
    
    【搜尋資料來源 (過去一週/一月)】：
    {news_text}
    
    請以繁體中文撰寫報告，包含：
    1. **📰 新聞懶人包**：最近發生什麼關鍵大事？(如營收、除息、新技術、外資動向)。
    2. **📈 市場情緒**：目前市場氣氛是樂觀、恐慌還是觀望？
    3. **⚖️ 多空分析**：
       - ✅ 利多因素
       - ⚠️ 風險隱憂
    4. **💡 操作建議**：針對現階段股價，建議的操作策略（買進/賣出/持有）。
    
    請務必基於提供的搜尋資料回答，不要憑空捏造。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text, news_text
    except Exception as e:
        return f"AI 發生錯誤: {e}", news_text

# --- 主介面 ---
st.title("🏦 AI 股市投資顧問 (穩定API版)")
st.markdown("使用 **Google Search API (Serper)**，保證抓得到資料，不再被擋。")

col1, col2 = st.columns([1, 1])
with col1:
    ticker_input = st.text_input("股票代號", placeholder="例如: 2303, 2330, TSLA")
with col2:
    country_input = st.selectbox("市場", ["台灣 (TW)", "美國 (US)"])

if st.button("🚀 啟動分析", type="primary"):
    if not gemini_key or not serper_key:
        st.error("❌ 請先在左側欄位輸入 Gemini 與 Serper 的 API Key")
    elif not ticker_input:
        st.warning("⚠️ 請輸入股票代號")
    else:
        # 1. 識別
        real_ticker, real_name = get_stock_identity(ticker_input, country_input)
        
        # 2. 構建精準查詢字串
        if country_input == "台灣 (TW)":
            search_query = f"{real_name} {real_ticker} 股價 新聞 營收"
        else:
            search_query = f"{real_ticker} stock news analysis"
            
        st.info(f"🔍 透過 Google API 搜尋：`{search_query}` ...")
        
        # 3. 搜尋
        search_result = search_google_serper(search_query, serper_key)
        
        # 4. 分析
        if "error" in search_result:
            st.error(f"API 連線失敗: {search_result['error']}")
        elif "organic" not in search_result:
            st.error("搜尋結果為空，請檢查 API Key 或關鍵字。")
        else:
            with st.spinner("🤖 AI 分析師正在閱讀報告..."):
                analysis, raw_news = analyze_market(search_result, real_ticker, real_name)
                
            st.success("✅ 分析完成！")
            
            # 顯示結果
            tab1, tab2 = st.tabs(["📊 投資分析報告", "📄 原始搜尋資料"])
            
            with tab1:
                st.markdown(analysis)
                
            with tab2:
                st.text(raw_news)
                st.json(search_result) # 顯示原始 JSON 供除錯
