# MediaManager 3.1.0

3.1 將 3.0 的低負載下載表格策略延伸到 Media Convert 與 Speech to Text。
只有畫面可見資料變更時才重建列表；處理中、閒置與隱藏頁面分別使用
500／1500／2500 ms 刷新，降低未啟用工作區的 CPU 與重繪成本。
