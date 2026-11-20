# Nguồn dữ liệu và nguồn dự phòng

Đọc file này khi người dùng hỏi dữ liệu lấy từ đâu, tốn bao nhiêu, hoặc muốn dữ liệu đầy đủ hơn.

## Nguồn miễn phí (mặc định, không cần đăng ký gì)

| Nền tảng | Nguồn | Có gì | Thiếu gì |
|---|---|---|---|
| X | FxTwitter (`api.fxtwitter.com`) | Khoảng 20 bài mới nhất mỗi tài khoản, đủ lượt xem, thích, trả lời, repost, quote, lưu | Tìm kiếm chập chờn, nhiều ngày trả về rỗng |
| TikTok | Trang nhúng hồ sơ công khai (`tiktok.com/embed/@kênh`) | 12 video mới nhất mỗi kênh, lượt xem, số follower | Không có thích, bình luận, chia sẻ, lưu. Chỉ thấy kênh trong danh sách |

Chi phí: 0 đồng. Giới hạn chính: TikTok không tìm được video của người ngoài danh sách theo dõi.

## Nguồn dự phòng có trả phí (tuỳ chọn)

Hai nguồn này tự hoạt động khi người dùng đặt biến môi trường tương ứng. Không có key thì hệ thống chạy như thường.

| | X: twitterapi.io | TikTok: Apify |
|---|---|---|
| Biến môi trường | `TWITTERAPI_IO_KEY` | `APIFY_TOKEN` |
| Khi nào được gọi | Khi FxTwitter không trả được một tài khoản, hoặc một truy vấn tìm kiếm rỗng | Lấy thích, bình luận, chia sẻ, lưu cho các video nhiều lượt xem nhất; hỏi lại kênh mà trang nhúng không trả được |
| Giá tham khảo | Khoảng 0,15 USD mỗi 1.000 bài | Từ khoảng 1,70 USD mỗi 1.000 video; Apify có 5 USD miễn phí mỗi tháng |
| Trần mỗi lượt quét | 60 lần gọi (`twitterapi_io_max_calls` trong `config/x/settings.json`) | 40 video và 15 kênh (`apify_enrich_max`, `apify_failover_max` trong `config/tiktok/settings.json`) |

Giá lấy từ trang của nhà cung cấp vào tháng 11/2026 và có thể đổi. Nhắc người dùng xem lại giá trước khi đăng ký.

Hai nguồn này chưa được kiểm thử với key thật. Lượt chạy đầu tiên có key có thể lộ lỗi đọc dữ liệu; nếu vậy báo người dùng đúng như thế.

### Cách bật

Người dùng tự đăng ký lấy key và tự đặt biến môi trường. Bạn không nhập, không lưu, không in key của họ. Đưa cho họ lệnh, mỗi lệnh một khối riêng.

Windows (PowerShell), xong thì mở lại Claude:

```powershell
[Environment]::SetEnvironmentVariable("TWITTERAPI_IO_KEY", "key-cua-ban", "User")
```

```powershell
[Environment]::SetEnvironmentVariable("APIFY_TOKEN", "token-cua-ban", "User")
```

Mac hoặc Linux: thêm vào `~/.zshrc` hoặc `~/.bashrc`:

```bash
export TWITTERAPI_IO_KEY="key-cua-ban"
```

```bash
export APIFY_TOKEN="token-cua-ban"
```

`viral.py status` cho biết mỗi nguồn đã bật hay chưa.

## Nguồn đã thử và không dùng

vxtwitter, Nitter, RSSHub: chặn truy cập tự động hoặc đã ngừng. Trang nhúng từng video TikTok và oEmbed: không có số tương tác. Trang video TikTok và API nội bộ của TikTok: có lớp chống bot, skill này không vượt qua.
