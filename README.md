# Proxy to Resin

自动将 EDT-Pages/Proxy-List 的三个代理列表合并成 Resin 可直接订阅的纯文本地址。

## 数据源

- HTTP  
  `https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/http.json`

- HTTPS  
  `https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/https.json`

- SOCKS5  
  `https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/socks5.json`

## 输出

GitHub Actions 每 8 小时自动执行一次：

```text
dist/resin.txt
```

文件格式：

```text
http://1.2.3.4:8080
https://5.6.7.8:443
socks5://9.10.11.12:1080
```

每行一个代理 URI，自动合并并去重。

## 部署到 GitHub

1. 新建一个 GitHub 仓库。
2. 将本项目所有文件上传到仓库根目录。
3. 建议仓库设为 Public，这样 raw.githubusercontent.com 地址可以直接访问。
4. 打开仓库的 **Actions** 页面。
5. 进入 **Update Resin Subscription**。
6. 点击 **Run workflow** 手动运行一次。
7. 等运行完成后确认出现：
   `dist/resin.txt`

## Resin 订阅地址

假设：

- GitHub 用户名：`YOUR_NAME`
- 仓库名：`proxy-to-resin`
- 分支：`main`

那么订阅地址是：

```text
https://raw.githubusercontent.com/YOUR_NAME/proxy-to-resin/main/dist/resin.txt
```

把它加入 Resin 的订阅即可。

## 自动更新频率

默认：

```yaml
- cron: "0 */8 * * *"
```

也就是每 8 小时运行一次。

GitHub Actions 的 cron 使用 UTC 时间。

## 本地测试

安装 Python 3 后：

```bash
python build.py
```

随后查看：

```text
dist/resin.txt
```

## 说明

当前版本只负责：

- 抓取三个 EDT 代理列表
- 提取代理 URI
- 合并
- 去重
- 输出 Resin 可使用的订阅文本

当前版本**不会测试代理是否真实可用**。

如果后续需要，可以继续增加：

- api64.ipify.org 可用性检测
- 并发检测
- 失败代理过滤
- 国家/地区过滤
- Residential / ISP 风险识别
- SQLite 历史记录
