import streamlit as st
from duckduckgo_search import DDGS
import google.generativeai as genai
import yfinance as yf
import time

# --- 設定頁面 ---
st.set_page_config(page_title="AI 股市投資助手 (增強版)", page_icon="📈", layout="wide")

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("輸入 Google Gemini API Key", type="password")
    st.markdown("[👉 點此獲取免費 Gemini API Key](https://aistudio.google.com/app/apikey)")
    st.info("💡 提示：台灣股票只需輸入「數字代號」即可（如 2330, 8069），系統會自動判斷上市或上櫃。")

# --- 核心 1: 把代號轉成公司名稱 ---
def get_stock_info(ticker_input, country):
    """
    輸入代號，回傳 (正式Ticker, 公司名稱)
    """
    ticker_input = ticker_input.strip().upper()
    
    # 美股直接回傳
    if country == "美國 (US)":
        return ticker_input, ticker_input 

    # 台股處理：嘗試 .TW (上市) 和 .TWO (上櫃)
    if ticker_input.isdigit():
        candidates = [f"{ticker_input}.TW", f"{ticker_input}.TWO"]
    else:
        # 使用者可能自己打了 .TW
        candidates = [ticker_input]

    for code in candidates:
        try:
            stock = yf.Ticker(code)
            # 嘗試讀取 info，如果讀不到通常會報錯或回傳空
            info = stock.info 
            if info and 'longName' in info:
                # 成功抓到資料
                short_name = info.get('shortName', info.get('longName'))
                st.success(f"✅ 識別成功：{code} ({short_name})")
                return code, short_name
        except Exception:
            continue
            
    # 如果都失敗，回傳原始輸入，賭賭看能不能搜到
    st.warning(f"⚠️ 無法透過代號取得詳細資料，將直接使用代號 `{ticker_input}` 搜尋，精準度可能較低。")
    return ticker_input, ticker_input

# --- 核心 2: 搜尋新聞 (優先用名稱搜) ---
def search_news(stock_symbol, company_name, country):
    results = []
    keywords = []

    # 建立搜尋關鍵字策略
    if country == "台灣 (TW)":
        # 關鍵：用「公司名稱」搜新聞，比用「代號」準確非常多
        name_clean = company_name.replace("台灣積體電路製造", "台積電") # 針對常見長名簡化，可擴充
        keywords = [
            f"{name_clean} 新聞",
            f"{name_clean} 營收",
            f"{stock_symbol} 股價分析",
            f"{name_clean} 展望"
        ]
    else:
        keywords = [
            f"{stock_symbol} stock news",
            f"{stock_symbol} forecast",
            f"{stock_symbol} analysis"
        ]

    st.write(f"🔍 正在搜尋關鍵字：{'、'.join(keywords[:2])} ...")

    # 1. 先試試 Yahoo Finance 內建新聞
    try:
        yf_stock = yf.Ticker(stock_symbol)
        yf_news = yf_stock.news
        if yf_news:
            for n in yf_news[:3]:
                results.append(f"[Yahoo] {n.get('title')} ({n.get('link')})")
    except:
        pass

    # 2. DuckDuckGo 廣泛搜尋
    with DDGS() as ddgs:
        for query in keywords:
            try:
                # max_results 設為 2，避免太多請求被封鎖
                ddg_res = list(ddgs.text(query, max_results=2, region='wt-wt'))
                for r in ddg_res:
                    results.append(f"[Web] {r['title']}: {r['body']}")
                time.sleep(0.5)
            except Exception as e:
                print(f"搜尋錯誤: {e}")

    # 去除重複內容
    return list(set(results))

# --- 核心 3: AI 分析 ---
def analyze_data(news_list, stock_symbol, company_name):
    if not news_list:
        return "❌ 真的找不到資料。可能原因：1. 公司太冷門 2. 短時間內發送太多請求被搜尋引擎阻擋。"
    
    news_text = "\n".join(news_list)
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位專業投資顧問。請分析 {company_name} ({stock_symbol})。
    
    【最新搜尋資料】：
    {news_text}
    
    請用繁體中文，針對「{company_name}」生成投資分析報告：
    1. **市場關注焦點**：最近新聞都在討論什麼？
    2. **多空判斷**：目前消息面偏向 🟢看多 / 🔴看空 / 🟡中立？
    3. **風險提示**：有什麼潛在壞消息？
    4. **建議**：適合進場嗎？為什麼？
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析錯誤: {e}"

# --- UI 介面 ---
st.title("🚀 AI 股票分析 (修正版)")

col1, col2 = st.columns([1, 1])
with col1:
    ticker = st.text_input("股票代號", placeholder="輸入 2330 或 NVDA")
with col2:
    country = st.selectbox("市場", ["台灣 (TW)", "美國 (US)"])

if st.button("開始分析", type="primary"):
    if not api_key:
        st.error("請輸入 API Key")
    elif not ticker:
        st.error("請輸入代號")
    else:
        with st.spinner("🔄 正在解析代號並搜尋資料..."):
            # 1. 取得正確代號與名稱
            real_ticker, real_name = get_stock_info(ticker, country)
            
            # 2. 搜尋新聞
            news = search_news(real_ticker, real_name, country)
            
            if news:
                with st.expander(f"查看 {len(news)} 筆原始資料"):
                    st.write(news)
                
                # 3. AI 分析
                result = analyze_data(news, real_ticker, real_name)
                st.markdown("---")
                st.markdown(result)
            else:
                st.error("找不到相關新聞，請稍後再試，或檢查代號是否正確。")
