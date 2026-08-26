# Proxy to Resin — Live Check Edition

自动抓取 EDT-Pages/Proxy-List 的 HTTP、HTTPS、SOCKS5 节点，
并在 GitHub Actions 中进行真实联网检测。

只有能够通过代理访问：

```text
https://api64.ipify.org?format=json
```

且返回合法 IP 地址的节点，才会写入 Resin 订阅。

## 输出文件

### Resin 订阅

```text
dist/resin.txt
```

每行一个可用代理：

```text
http://1.2.3.4:8080
https://5.6.7.8:443
socks5://9.10.11.12:1080
```

### 检测统计

```text
dist/stats.json
```

包含：

- 抓取总数
- 存活数量
- 失败数量
- 各协议数量
- 延迟
- 出口 IP
- 实际测试方式

## GitHub Actions

默认每 8 小时运行一次。

工作流已经使用：

```yaml
actions/checkout@v7
actions/setup-python@v7
```

避免旧版 Node.js 20 action 的弃用 warning。

## 可调参数

在：

```text
.github/workflows/update.yml
```

中修改：

```yaml
PROXY_TEST_CONCURRENCY: "64"
PROXY_TEST_TIMEOUT: "8"
PROXY_TEST_RETRIES: "1"
PROXY_TEST_URL: "https://api64.ipify.org?format=json"
```

建议 GitHub Actions：

- 并发：32～100
- 超时：5～10 秒
- 重试：0～1 次

如果代理数量非常多，可以把并发提高到 100，但不建议一开始就设得太高。

## Resin 订阅地址

例如：

- GitHub 用户名：`InxMM`
- 仓库：`SUBX`
- 分支：`main`

订阅地址：

```text
https://raw.githubusercontent.com/InxMM/SUBX/main/dist/resin.txt
```

## 重要保护

如果：

- 三个上游全部抓取失败；或
- 本轮检测结果为 0 个存活代理；

程序会直接报错退出，**不会覆盖上一次正常生成的 resin.txt**。

这样可以避免因为 ipify 临时异常或 GitHub 网络异常把订阅清空。

## HTTPS 节点兼容

部分公开代理列表将：

```text
https://IP:PORT
```

用于表示“支持 HTTPS CONNECT 的代理”，但代理入口本身实际是普通 HTTP。

因此检测逻辑：

1. 先按原始 `https://` 测试；
2. 失败后额外尝试 `http://同IP:端口`；
3. 如果测试成功，最终 Resin 输出仍保留原始 URI。

## 手动运行

GitHub：

```text
Actions
→ Update Resin Subscription
→ Run workflow
```

## 本地运行

```bash
python -m pip install -r requirements.txt
python build.py
```
