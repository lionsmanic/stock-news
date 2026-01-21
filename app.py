import streamlit as st
from duckduckgo_search import DDGS
import google.generativeai as genai
import yfinance as yf
import time
from datetime import datetime

# --- 設定頁面配置 ---
st.set_page_config(page_title="AI 全方位股市投資助手", page_icon="💹", layout="wide")

# --- 側邊欄：設定與說明 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("輸入 Google Gemini API Key", type="password")
    st.markdown("[👉 點此獲取免費 Gemini API Key](https://aistudio.google.com/app/apikey)")
    st.markdown("---")
    st.markdown("### 💡 搜尋策略說明")
    st.info("""
    本系統採用 **多源頭聚合搜尋**：
    1. **Yahoo Finance**: 獲取官方公告與主流財經新聞。
    2. **DuckDuckGo**: 廣泛搜尋網路討論、產業分析與小道消息。
    3. **產業關聯**: 自動搜尋該公司所屬產業的趨勢。
    """)

# --- 工具函數：獲取 Yahoo Finance 新聞 ---
def get_yahoo_news(ticker_symbol):
    news_content = []
    try:
        stock = yf.Ticker(ticker_symbol)
        news_list = stock.news
        
        if news_list:
            for item in news_list[:5]: # 取前 5 則
                title = item.get('title', '無標題')
                link = item.get('link', '#')
                # 嘗試獲取出版商
                publisher = item.get('publisher', 'Yahoo Finance')
                news_content.append(f"[Yahoo] 標題: {title}\n來源: {publisher}\n連結: {link}")
    except Exception as e:
        print(f"Yahoo Finance 搜尋錯誤: {e}")
    
    return news_content

# --- 工具函數：DuckDuckGo 廣泛搜尋 ---
def get_ddg_news(keywords):
    results = []
    with DDGS() as ddgs:
        for query in keywords:
            try:
                # 每個關鍵字抓取前 3 條，region='wt-wt' 代表全球，也可設 'tw-tz'
                search_res = list(ddgs.text(query, max_results=3, region='wt-wt'))
                for r in search_res:
                    results.append(f"[Web] 標題: {r['title']}\n摘要: {r['body']}\n連結: {r['href']}")
                time.sleep(0.5) 
            except Exception as e:
                print(f"DDG 搜尋 '{query}' 錯誤: {e}")
    return results

# --- 核心函數：綜合搜尋邏輯 ---
def aggregate_news(ticker, country):
    st.status("🕵️‍♂️ 正在啟動多源頭搜尋引擎...", expanded=True)
    
    # 1. 代號標準化處理
    search_ticker = ticker.upper().strip()
    company_name_query = ticker # 用來搜文字新聞的備用名稱
    
    if country == "台灣 (TW)":
        if search_ticker.isdigit(): # 如果是純數字 (如 2330)
            search_ticker = f"{search_ticker}.TW"
        # 增加中文關鍵字
        keywords = [
            f"{ticker} 營收", 
            f"{ticker} 股價分析", 
            f"{ticker} 產業前景"
        ]
    else:
        # 美股關鍵字
        keywords = [
            f"{search_ticker} stock forecast", 
            f"{search_ticker} revenue analysis", 
            f"{search_ticker} industry trends"
        ]

    all_news = []

    # 2. 執行 Yahoo Finance 搜尋 (針對個股最精準)
    st.write(f"📡 正在連線 Yahoo Finance 資料庫搜尋 `{search_ticker}`...")
    yf_news = get_yahoo_news(search_ticker)
    if yf_news:
        all_news.extend(yf_news)
        st.write(f"✅ 成功取得 Yahoo 新聞 {len(yf_news)} 則")
    else:
        st.warning("⚠️ Yahoo Finance 未回傳資料，嘗試擴大網路搜尋...")

    # 3. 執行 DuckDuckGo 搜尋 (補充產業與網路文章)
    st.write(f"🌐 正在掃描全網關於 `{ticker}` 與產業的討論...")
    ddg_news = get_ddg_news(keywords)
    if ddg_news:
        all_news.extend(ddg_news)
        st.write(f"✅ 成功取得網路文章 {len(ddg_news)} 則")

    return "\n\n".join(all_news)

# --- 核心函數：AI 分析 ---
def analyze_stock_comprehensive(news_text, ticker, country):
    if not news_text or len(news_text) < 50:
        return "❌ 資料不足：搜尋到的新聞過少，無法進行有效分析。建議檢查股票代號是否正確，或該公司過於冷門。"

    genai.configure(api_key=api_key)
    # 使用 1.5 Pro 模型 (若免費額度允許) 或 Flash，Pro 對長文理解更好
    model = genai.GenerativeModel('gemini-1.5-flash') 

    prompt = f"""
    你是一位華爾街等級的資深投資顧問。請根據以下蒐集到的【多來源新聞彙整】，對股票代號：{ticker} ({country}) 進行深度分析。

    【新聞與數據彙整】：
    {news_text}

    請以**繁體中文**撰寫一份結構清晰的投資報告，包含以下區塊：

    ### 1. 📊 市場情緒儀表板
    * **情緒燈號**：(🔴悲觀 / 🟡中立 / 🟢樂觀)
    * **關鍵一句話**：用一句話總結目前市場對該公司的看法。

    ### 2. 🔥 近期重大事件解析
    * 列出 3-5 點新聞中提到的關鍵事件（如財報發布、新產品、收購、法規變動等），並簡述其對股價的潛在影響。

    ### 3. 🔭 產業鏈與競爭分析
    * 分析該公司所處產業的整體狀況（是成長中、衰退中還是盤整中？）。
    * 若新聞有提到競爭對手，請一併進行比較。

    ### 4. 💡 投資建議與策略
    * **評級**：(強力買進 / 分批佈局 / 觀望持有 / 減碼賣出)
    * **操作建議**：針對短線交易者與長線投資者分別給出建議。
    * **風險提示**：列出目前最大的隱憂（如匯率、政策、供應鏈等）。

    (請確保語氣專業客觀，並在最後加上免責聲明)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析連線失敗: {str(e)}"

# --- 主介面 ---
st.title("💹 AI 全方位股市投資助手 V2.0")
st.markdown("### 結合 Yahoo Finance 與 全網搜尋，提供更精準的投資建議")

col1, col2 = st.columns([2, 1])
with col1:
    ticker_input = st.text_input("輸入股票代號", placeholder="例如: 2330, NVDA, TSLA")
with col2:
    market_select = st.selectbox("選擇市場", ["台灣 (TW)", "美國 (US)"])

if st.button("🚀 啟動深度分析", type="primary"):
    if not api_key:
        st.error("❌ 請先在左側欄位輸入 API Key")
    elif not ticker_input:
        st.warning("⚠️ 請輸入股票代號")
    else:
        # 顯示進度條
        with st.spinner('🔍 正在進行全網深度搜查...'):
            raw_news = aggregate_news(ticker_input, market_select)
        
        if raw_news:
            with st.expander("📄 點此檢視 AI 閱讀的原始新聞資料"):
                st.text(raw_news)
            
            with st.spinner('🧠 AI 首席分析師正在撰寫報告...'):
                report = analyze_stock_comprehensive(raw_news, ticker_input, market_select)
                
            st.markdown("---")
            st.markdown(report)
        else:
            st.error("❌ 搜遍全網仍找不到資料，請確認代號是否正確 (台股請確認是上市櫃公司)。")
