# SEOUL closet｜韓選衣櫥

韓式服裝電商：前台選購、7-11 門市取貨結帳、業主後台批次上圖與依序出貨。

只需 **Python 3.10+ 標準庫**，不需 pip 安裝套件。

## 本機啟動

```bash
python3 server.py
```

或：

```bash
chmod +x start.sh
./start.sh
```

瀏覽器開啟：

| 頁面 | 網址 |
| --- | --- |
| 前台選購 | http://127.0.0.1:8080/ |
| 業主後台 | http://127.0.0.1:8080/admin |

第一次啟動會自動建立資料庫，並產生 **50** 件示範商品。

## 後台帳號

| 項目 | 值 |
| --- | --- |
| 帳號 | `admin` |
| 初始密碼 | `2wsxcde3` |

密碼超過 **90 天**未更換時，後台會顯示提醒。請到「更改密碼」更新。

正式上線請立刻改密碼，不要使用預設值。

## 功能

**前台**

- 商品列表、分類篩選、購物袋
- 結帳欄位：姓名、手機、7-11 門市名稱
- 訂單即時寫入後台

**後台**

- 一次最多上傳 **30** 張衣服圖片，每張圖自動新增一筆前台商品
- 訂單由舊到新排列，可依序點「出貨」
- 更改密碼並重置 90 天提醒週期

## 目錄

```
server.py          網站伺服器（標準庫）
start.sh           啟動腳本
public/            前台／後台頁面、樣式、商品圖
public/uploads/    後台上傳的新圖（執行後產生）
data/              SQLite 資料庫（執行後產生 shop.db）
```

## 上傳到 GitHub

1. 到 GitHub 新增空白 Repository（不要勾 README）
2. 解壓本包後執行：

```bash
cd seoul-closet
git init
git add .
git commit -m "Initial commit: SEOUL closet shop"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<倉庫名>.git
git push -u origin main
```

他人 clone 後同樣執行 `python3 server.py` 即可使用。

## 注意

- 此為單機示範站，未接金流、未接 7-11 官方 API
- 資料存在本機 `data/shop.db`，上傳圖在 `public/uploads/`
- 對外公開前請修改 `server.py` 裡的 `SECRET` 與預設密碼
