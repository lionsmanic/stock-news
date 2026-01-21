import streamlit as st
from duckduckgo_search import DDGS
import google.generativeai as genai
import yfinance as yf
import twstock
import time

# --- 設定頁面 ---
st.set_page_config(page_title="AI 股市狙擊手", page_icon="🎯", layout="wide")

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("輸入 Google Gemini API Key", type="password")
    st.markdown("[👉 點此獲取免費 Gemini API Key](https://aistudio.google.com/app/apikey)")
    st.info("💡 強力模式：已啟用 twstock 本地資料庫，台股代號識別率 100%。")

# --- 核心 1: 獲取公司名稱 (最關鍵的一步) ---
def get_company_name(ticker, country):
    ticker = ticker.strip().upper()
    
    # === 台灣股票處理 (使用 twstock 本地庫) ===
    if country == "台灣 (TW)":
        # twstock 是一個專門的台股庫，codes 字典裡存有代號對應的資訊
        if ticker in twstock.codes:
            stock_info = twstock.codes[ticker]
            name = stock_info.name # 例如：聯華電子
            st.success(f"✅ 識別成功 (本地庫)：{ticker} -> {name}")
            return ticker, name
        else:
            # 萬一本地庫找不到，回傳原始代號嘗試硬搜
            st.warning(f"⚠️ 本地資料庫找不到代號 {ticker}，將直接使用代號搜尋。")
            return ticker, ticker

    # === 美國股票處理 (使用 yfinance) ===
    else:
        try:
            stock = yf.Ticker(ticker)
            # 嘗試抓取短名
            name = stock.info.get('shortName') or stock.info.get('longName') or ticker
            st.success(f"✅ 識別成功 (Yahoo)：{ticker} -> {name}")
            return ticker, name
        except Exception as e:
            st.warning(f"⚠️ Yahoo 抓取名稱失敗，將使用代號搜尋: {e}")
            return ticker, ticker

# --- 核心 2: 搜尋新聞 (使用名稱 + 代號) ---
def search_web_news(ticker, name, country):
    results = []
    
    # 設定搜尋關鍵字策略
    if country == "台灣 (TW)":
        # 關鍵：同時搜「名稱」和「代號」
        keywords = [
            f"{name} {ticker} 新聞",        # 針對性最強：聯華電子 2303 新聞
            f"{name} 營收分析",             # 找基本面
            f"{name} 股價展望 {ticker}"     # 找預測
        ]
    else:
        keywords = [
            f"{name} stock news",
            f"{ticker} stock forecast",
            f"{name} financial results"
        ]

    st.markdown(f"🔍 **搜尋引擎啟動，正在搜尋：** `{keywords[0]}` ...")

    with DDGS() as ddgs:
        for query in keywords:
            try:
                # 每個關鍵字抓 3 筆，並暫停一下避免被鎖
                search_res = list(ddgs.text(query, max_results=3, region='wt-wt'))
                if search_res:
                    for r in search_res:
                        # 格式化輸出
                        results.append(f"標題: {r['title']}\n摘要: {r['body']}\n連結: {r['href']}")
                time.sleep(0.7)
            except Exception as e:
                print(f"搜尋 '{query}' 時發生錯誤: {e}")
                
    return list(set(results)) # 去除重複

# --- 核心 3: AI 分析 ---
def analyze_stock(news_text, ticker, name):
    if not news_text:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位專業的證券分析師。請根據以下網路上蒐集到的最新資訊，分析「{name} ({ticker})」。
    
    【搜尋到的資訊】：
    {news_text}
    
    請以繁體中文回答，結構如下：
    1. **🧐 懶人包摘要**：用兩句話講完最近發生什麼大事。
    2. **⚖️ 多空消息分析**：
       - 利多消息 (Positive)：列出 2-3 點。
       - 利空消息 (Negative)：列出 2-3 點 (包含風險)。
    3. **🎯 投資建議結論**：
       - 給予評級：(強力買進 / 分批佈局 / 觀望 / 賣出)
       - 原因說明。
    
    (注意：若資訊中包含過期新聞，請自行過濾，著重於最新趨勢。)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 腦力激盪失敗: {str(e)}"

# --- 主程式 ---
st.title("🎯 AI 股市狙擊手 (精準名稱版)")
st.markdown("輸入代號 -> 自動轉換公司名 -> 搜爆全網新聞 -> AI 結論")

col1, col2 = st.columns([1, 1])
with col1:
    ticker_input = st.text_input("股票代號", placeholder="例如: 2303, 2330, NVDA")
with col2:
    country_input = st.selectbox("市場", ["台灣 (TW)", "美國 (US)"])

if st.button("🚀 開始分析", type="primary"):
    if not api_key:
        st.error("❌ 請輸入 API Key")
    elif not ticker_input:
        st.warning("⚠️ 請輸入代號")
    else:
        # 1. 轉換名稱
        real_ticker, real_name = get_company_name(ticker_input, country_input)
        
        # 2. 搜尋
        with st.spinner(f"正在閱讀關於【{real_name}】的網路文章..."):
            news_data = search_web_news(real_ticker, real_name, country_input)
        
        # 3. 判斷與分析
        if news_data:
            with st.expander(f"📄 檢視原始搜尋資料 ({len(news_data)} 筆)"):
                st.text("\n\n".join(news_data))
            
            with st.spinner("🤖 AI 正在撰寫分析報告..."):
                analysis = analyze_stock("\n".join(news_data), real_ticker, real_name)
                
            if analysis:
                st.markdown("---")
                st.markdown(analysis)
            else:
                st.error("AI 無法生成回應，請檢查 API Key 額度。")
        else:
            st.error(f"❌ 搜遍全網找不到關於「{real_name} ({real_ticker})」的資料。")
            st.markdown("可能是搜尋引擎暫時阻擋，請等待 1 分鐘後再試。")
