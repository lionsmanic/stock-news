import streamlit as st
from duckduckgo_search import DDGS
import google.generativeai as genai
import time

# --- 設定頁面配置 ---
st.set_page_config(page_title="AI 股市投資助手", page_icon="📈", layout="wide")

# --- 側邊欄：API Key 設定 ---
st.sidebar.header("⚙️ 設定")
api_key = st.sidebar.text_input("輸入 Google Gemini API Key", type="password")
st.sidebar.markdown("[👉 點此獲取免費 Gemini API Key](https://aistudio.google.com/app/apikey)")

# --- 核心函數：搜尋新聞 ---
def search_financial_news(ticker, country):
    results = []
    
    # 根據國家調整搜尋關鍵字
    if country == "台灣 (TW)":
        keywords = [f"{ticker} 股票 新聞", f"{ticker} 營收 產業分析", f"{ticker} stock news"]
    else:
        keywords = [f"{ticker} stock news", f"{ticker} financial analysis", f"{ticker} stock forecast"]

    st.info(f"🔍 正在搜尋 {ticker} ({country}) 的最新相關資訊...")
    
    # 使用 DuckDuckGo 搜尋 (免費且無須 Key)
    with DDGS() as ddgs:
        for query in keywords:
            try:
                # 每個關鍵字抓取前 3 條結果
                search_res = list(ddgs.text(query, max_results=3))
                for r in search_res:
                    results.append(f"標題: {r['title']}\n連結: {r['href']}\n摘要: {r['body']}")
            except Exception as e:
                st.warning(f"搜尋 '{query}' 時發生錯誤: {e}")
            time.sleep(1) # 避免請求過快
            
    return "\n\n".join(results)

# --- 核心函數：AI 分析 ---
def analyze_stock(news_text, ticker, country):
    if not news_text:
        return "無法取得足夠的新聞資料進行分析。"

    # 設定 Gemini 模型
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # 使用輕量快速模型

    prompt = f"""
    你是一位專業的金融投資分析師。請根據以下蒐集到的最新新聞與財經資訊，分析股票代號：{ticker} ({country})。
    
    【搜尋到的資訊】：
    {news_text}
    
    請以繁體中文回答，並依照以下格式輸出：
    1. **市場情緒摘要**：綜合目前新聞對該公司的情緒（看多/看空/中立）。
    2. **最新關鍵消息**：列出 3 點最重要的近期事件或財報數據。
    3. **產業趨勢**：該公司所處產業目前的狀況。
    4. **投資建議**：
       - 給予評級（強力買進 / 買進 / 觀望 / 賣出）。
       - 說明理由（風險與機會）。
    
    注意：這只是基於新聞的分析，請在最後加上「投資有風險，請自行評估」的警語。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析失敗: {str(e)}"

# --- 主介面 UI ---
st.title("📈 AI 智能股市分析助手")
st.markdown("輸入股票代號，自動搜集最新中英文新聞並給予投資建議。")

col1, col2 = st.columns(2)

with col1:
    ticker = st.text_input("輸入股票代號 (例如: 2330 或 NVDA)", placeholder="例如: 2330")
with col2:
    country = st.selectbox("選擇市場", ["台灣 (TW)", "美國 (US)"])

analyze_btn = st.button("🚀 開始分析", type="primary")

# --- 執行邏輯 ---
if analyze_btn:
    if not api_key:
        st.error("❌ 請先在左側欄位輸入 Google Gemini API Key")
    elif not ticker:
        st.warning("⚠️ 請輸入股票代號")
    else:
        try:
            # 1. 搜尋新聞
            news_data = search_financial_news(ticker, country)
            
            if news_data:
                with st.expander("👀 查看原始搜尋到的新聞摘要 (除錯用)"):
                    st.text(news_data)

                # 2. AI 分析
                with st.spinner('🤖 AI 正在閱讀新聞並撰寫報告中...'):
                    analysis_result = analyze_stock(news_data, ticker, country)
                
                # 3. 顯示結果
                st.success("✅ 分析完成！")
                st.markdown("---")
                st.markdown(analysis_result)
            else:
                st.error("找不到相關新聞資料，請確認代號是否正確。")
                
        except Exception as e:
            st.error(f"發生未預期的錯誤: {e}")
