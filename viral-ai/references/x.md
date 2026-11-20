# Nền tảng X

## Nguồn dữ liệu

FxTwitter API v2 (miễn phí, không cần key) cho timeline từng tài khoản và tìm kiếm, có đủ lượt xem, thích, repost, quote, trả lời, lưu. X syndication làm dự phòng. Nguồn dự phòng trả phí (twitterapi.io): xem `nguon-du-phong.md`.

## Bước 1: đọc bảng tóm tắt

Thu thập mất khoảng 2–4 phút.

- Dưới 80% tài khoản lấy được, hoặc dưới 100 bài trong cửa sổ: FxTwitter đang trục trặc. Chờ 10 phút rồi chạy lại một lần. Nếu vẫn vậy, làm tiếp với dữ liệu có được và nói rõ trong báo cáo.
- Nhiều truy vấn tìm kiếm rỗng là chuyện thường, tìm kiếm của FxTwitter chập chờn.
- Cùng một handle nằm trong danh sách "Không lấy được" nhiều ngày: handle đã đổi tên. Báo người dùng.

## Ba rổ ứng viên (`origin`)

| Giá trị | Nghĩa |
|---|---|
| `own` | Bài của hãng, KOL, KOC trong danh sách theo dõi |
| `amplified` | Bài của người khác được tài khoản trong danh sách repost hay quote |
| `discovery` | Bài tìm được qua tìm kiếm |

## Đọc tín hiệu

| Dấu hiệu trong dữ liệu | Ý nghĩa | Gợi ý định dạng |
|---|---|---|
| `outlier_ratio` cao, tài khoản nhỏ | Viral thật, nội dung tự lan | Ý tưởng có sức tự thân, Việt hoá ý chính |
| `luu-nhieu` (lưu ≥ 45% thích) | Có giá trị tham khảo | Hướng dẫn từng bước, kêu gọi lưu |
| `tranh-luan` (trả lời ≥ 25% thích) | Chia phe | Nói trước ống kính, nêu quan điểm, hỏi ngược |
| `nhieu-quote` | Ai cũng muốn thêm ý kiến | Phản ứng, thêm góc nhìn riêng |
| `lan-truyen-manh` | Tin đáng báo cho người khác | Tin nhanh |
| `kol-khuech-dai` | Người có uy tín xác nhận | Nhắc tên người chia sẻ để tăng độ tin |
| `con-moi` + tốc độ cao | Cửa sổ còn mở | Làm ngay, bản ngắn trước |
| `er` dưới 0,4% | Lượt xem có thể do quảng cáo | Thận trọng, nêu trong `risk` |

## Loại thêm

- Nhãn `nghi-quang-cao` mà không có giá trị nội dung.
- Nhãn `co-community-note`: nội dung đã bị cộng đồng đính chính.

## Bẫy riêng

- Nội dung chính của nhiều bài nằm trong ảnh, video hoặc bài dài (`long_post`). `candidates.json` chỉ có phần chữ, cắt ở 900 ký tự.
- Bài quote: đọc cả trường `quote` để hiểu bài đang phản ứng với điều gì.
