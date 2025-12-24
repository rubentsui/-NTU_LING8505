使用說明 (Docker 版本)
======================

這個版本使用 Docker 容器技術，您不需要在電腦上安裝 Python 或 Node.js，只需要安裝 Docker Desktop 即可。

準備工作：
---------
1. 請先下載並安裝 Docker Desktop：
   https://www.docker.com/products/docker-desktop/
   
2. 安裝完成後，請啟動 Docker Desktop 程式，並確保它在背景執行中 (右下角系統列可以看到鯨魚圖示)。

如何啟動：
---------
1. 雙擊執行 `start_docker.bat` 檔案。
2. 第一次執行會花一些時間下載和安裝環境 (約 3-5 分鐘)，請耐心等待。
3. 當看到螢幕上出現 Translation Dashboard 啟動成功的訊息後：
   - 前端畫面：打開瀏覽器輸入 http://localhost:3000
   - 後端 API：http://localhost:8000

如何關閉：
---------
1. 在執行的黑色視窗中按 `Ctrl + C` 可以停止服務。
2. 或者雙擊執行 `stop_docker.bat` 來完整關閉並移除容器。

疑難排解：
---------
Q: 執行 start_docker.bat 一閃而過？
A: 請確認您的 Docker Desktop 是否已經開啟並正常運作中。

Q: 網頁打不開？
A: 請確保這個黑色視窗沒有被關閉。如果是第一次執行，可能還在建置中，請多等一下直到看到 "Started" 字樣。
