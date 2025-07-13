#!/usr/bin/env python3
# fix_and_check_csv.py
import os, csv
from pathlib import Path
import pandas as pd
from tqdm import tqdm

BASE_DIR      = Path("~/Quantify/okx/data").expanduser()
OUT_FILE      = BASE_DIR / "invalid_csv_paths.txt"
EXPECTED_HDR  = ["trade_date", "open", "high", "low", "close", "vol1", "vol"]
EXPECTED_COLS = len(EXPECTED_HDR)



# 20250602 1500  检查是不是我要的格式
def is_valid_csv(file_path: Path) -> bool:
    """返回 True 表示格式正确，False 表示不符合要求"""
    try:
        with file_path.open("r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            if header != EXPECTED_HDR:
                return False
            # 再随机抽查前 100 行（或文件行数不足时全部）是否列数正确
            for i, row in enumerate(reader):
                if len(row) != EXPECTED_COLS:
                    return False
                if i >= 99:          # 抽样 100 行即可
                    break

            for i, row in enumerate(reader, start=2):
                if i > 10:
                    break
                # 列数必须恰好 7
                if len(row) != EXPECTED_COLS:
                    print(f"⚠️  {file_path} 第 {i} 行列数不符")
                    return False
                # 不允许空字段
                if any(field.strip() == "" for field in row):
                    print(f"⚠️  {file_path} 第 {i} 行含空值")
                    return False
        return True
    except Exception:
        # 读文件失败或 CSV 解析出错，也视为不符合
        return False

# 20250602 1500 检查整体是否是从币安下载的数据格式，如果是的话 直接转化
def try_fix_binance_kline(file_path: Path) -> bool:
    """
    若是 12 列的 Binance K 线文件，则就地修正为 7 列格式。
    返回 True = 修复成功 / 本就合规；False = 修复失败或不符合任何格式。
    """
    try:
        # 先用 header=None 读一行，判断列数
        sample = pd.read_csv(file_path, nrows=5, header=None)
        if sample.shape[1] != 12:
            return False          # 非 12 列文件，交给外层判定

        # 1⃣ 读完整 CSV（无表头）
        cols_12 = [
            "Open time", "Open", "High", "Low", "Close", "Volume",
            "Close time", "Quote asset volume", "Trades",
            "Taker buy base", "Taker buy quote", "Ignore"
        ]
        df = pd.read_csv(file_path, header=None, names=cols_12)

        # 2⃣ 时间列转换
        open_time = pd.to_numeric(df["Open time"], errors="coerce")
        if open_time.max() > 1e13:          # 微秒级或纳秒级
            open_time = open_time // 1000   # 降到毫秒级
        df["trade_date"] = pd.to_datetime(open_time, unit="ms")

        # 3⃣ 列映射 & 重排
        df["vol1"] = df["Quote asset volume"]
        df["vol"]  = df["Volume"]
        df = df[["trade_date", "Open", "High", "Low", "Close", "vol1", "vol"]]
        df.columns = df.columns.str.lower()

        # 4⃣ 覆写原文件
        df.to_csv(file_path, index=False)
        print(f"✔️  修复完成：{file_path}")
        return True
    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False


# 20250602 1500 时候检查是否满足要求
def check_7col_format(file_path: Path) -> bool:
    """验证文件是否已是目标 7 列格式"""
    try:
        with file_path.open("r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            if header != EXPECTED_HDR:
                return False
            # 抽查前 100 行列数
            for i, row in enumerate(reader):
                if len(row) != EXPECTED_COLS:
                    return False
                if i >= 99:
                    break
        return True
    except Exception:
        print('cao')
        return False




# 20250602 1500  有段代码搞错了，直接出岔子了，所以删掉错误的文件
# ───────────────────────── 🆕 0. 先判断是否需要删除 ────────────────────────────
def mark_and_delete_if_repeated_header(file_path: Path, threshold: int = 2) -> bool:
    """
    若文件中出现超过 threshold 行包含 'open,high,low,close'，则删除文件并返回 True。
    """
    try:
        with file_path.open("r") as f:
            count = sum(1 for line in f if "open,high,low,close" in line.lower())
        if count >= threshold:
            print(f"🗑️  删除文件（重复 header {count} 行）: {file_path}")
            file_path.unlink(missing_ok=True)
            return True
        return False
    except Exception as e:
        print(f"❌ 检查/删除失败 {file_path}: {e}")
        return False



def main():
    invalid_paths = []

    for root, _, files in os.walk(BASE_DIR):
        for fname in tqdm(files):
            if not fname.lower().endswith(".csv"):
                continue
            fpath = Path(root) / fname
            if str(fpath).find('coin_change_data') != -1:
                continue
            if str(fpath).find('SHIB') == -1:
                continue
            # 0⃣ 出现过多 header → 直接删并跳过
            if mark_and_delete_if_repeated_header(fpath):
                continue

            # 尝试修复 12 列 Binance 文件
            if not is_valid_csv(fpath):
                fixed = try_fix_binance_kline(fpath)
                # 如果修复成功，文件现在应当是 7 列合规；继续校验
                if not check_7col_format(fpath):
                    invalid_paths.append(str(fpath.resolve()))

    # 写出不合规清单
    OUT_FILE.write_text("\n".join(invalid_paths))
    print(f"\n✅ 扫描结束！不合规文件数: {len(invalid_paths)}")
    print(f"  详情见: {OUT_FILE}")

if __name__ == "__main__":
    main()