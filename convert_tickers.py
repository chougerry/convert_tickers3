import pandas as pd
import yfinance as yf

def read_csv_auto_encoding(filepath):
    # 自動相容 UTF-8 與 Excel 預設的 Big5 編碼
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(filepath, dtype={0: str}, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("無法辨識 CSV 檔案編碼，請確認檔案格式。")

def find_valid_tickers_batch(codes, batch_size=100):
    valid_map = {}
    total = len(codes)
    
    for i in range(0, total, batch_size):
        batch = codes[i:i + batch_size]
        print(f"正在驗證第 {i + 1} 到 {min(i + batch_size, total)} 檔上市櫃屬性...", flush=True)
        
        # 1. 先批次測試上市 (.TW)
        tw_candidates = [f"{c}.TW" for c in batch]
        data_tw = yf.download(tw_candidates, period="5d", group_by="ticker", progress=False)
        
        not_found_in_tw = []
        for c in batch:
            t_tw = f"{c}.TW"
            try:
                df_c = data_tw if len(tw_candidates) == 1 else data_tw[t_tw]
                if not df_c.dropna(subset=["Close"]).empty:
                    valid_map[c] = t_tw
                else:
                    not_found_in_tw.append(c)
            except Exception:
                not_found_in_tw.append(c)
                
        # 2. 剩下的批次測試上櫃 (.TWO)
        if not_found_in_tw:
            two_candidates = [f"{c}.TWO" for c in not_found_in_tw]
            data_two = yf.download(two_candidates, period="5d", group_by="ticker", progress=False)
            
            for c in not_found_in_tw:
                t_two = f"{c}.TWO"
                try:
                    df_c = data_two if len(two_candidates) == 1 else data_two[t_two]
                    if not df_c.dropna(subset=["Close"]).empty:
                        valid_map[c] = t_two
                except Exception:
                    pass
                    
    return valid_map

def convert_csv(input_file="raw_stocks.csv", output_file="stock_list.csv"):
    print(f"正在讀取 {input_file}...", flush=True)
    df = read_csv_auto_encoding(input_file)
    
    code_col = df.columns[0]
    name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    
    # 清理空白字元並保留原始代號
    df[code_col] = df[code_col].astype(str).str.strip()
    unique_codes = df[code_col].dropna().unique().tolist()
    
    valid_map = find_valid_tickers_batch(unique_codes)
    df["Ticker"] = df[code_col].map(valid_map)
    
    # 顯示找不到的股票（例如興櫃、已下市或代號輸入錯誤）
    missing = df[df["Ticker"].isna()]
    if not missing.empty:
        print(f"警告：以下 {len(missing)} 檔在 Yahoo Finance 找不到上市/上櫃資料，已略過：", flush=True)
        print(missing[[code_col, name_col]].to_string(index=False), flush=True)
        
    valid_df = df.dropna(subset=["Ticker"]).copy()
    valid_df = valid_df[["Ticker", name_col]]
    valid_df.columns = ["Ticker", "Name"]
    valid_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"轉換完成！共 {len(valid_df)} 檔股票已儲存至 {output_file}", flush=True)

if __name__ == "__main__":
    convert_csv()
