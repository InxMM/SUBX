# SUBX Resin Converter

This version performs no proxy probing.

It only:

1. downloads EDT-Pages HTTP/HTTPS/SOCKS5 JSON lists;
2. extracts each `proxy` URI;
3. merges and deduplicates the entries;
4. writes `dist/resin.txt`;
5. commits the updated subscription every 8 hours.

Resin is responsible for health checking the imported nodes.

For repository `InxMM/SUBX`, the subscription URL is:

https://raw.githubusercontent.com/InxMM/SUBX/main/dist/resin.txt
