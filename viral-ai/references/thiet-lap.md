# Thiết lập lần đầu và tìm kênh mẫu

Đọc file này khi `status` báo CHƯA CÀI ĐẶT hoặc THIẾT LẬP HỒ SƠ KÊNH, và khi người dùng muốn thêm kênh để học theo.

Mục tiêu: người dùng trả lời vài câu hỏi bằng lời thường, 10 phút sau có lượt quét đầu tiên. Họ không phải mở file nào.

## 1. Cài đặt

Chạy `viral.py setup`. Lệnh tạo thư mục làm việc `viral-ai-data` ở thư mục hiện tại, chép cấu hình mẫu vào (không ghi đè file có sẵn), ghi nhớ vị trí cho các phiên sau, và in trạng thái. Nếu người dùng muốn đặt ở nơi khác, thêm `--home <thư mục>`.

Sau đó nói với người dùng một câu: dữ liệu nằm ở đâu, và bước kế là kể về kênh của họ.

## 2. Phỏng vấn hồ sơ kênh

Hỏi gọn, một lượt, tối đa ba câu:

1. Bạn có những kênh TikTok nào? Gửi link hoặc tên kênh.
2. Mỗi kênh nói với ai? (ví dụ: người đi làm, chủ doanh nghiệp, sinh viên)
3. Có kênh nào bạn đang thích và muốn học theo không? (không có cũng được)

Đừng hỏi thứ đo được. Với mỗi kênh của họ, chạy:

```
viral.py check tiktok <tên kênh>
```

Lệnh in số follower, mức thường (lượt xem trung vị), và 3 video nhiều lượt xem nhất kèm caption. Từ đó tự điền:

- **Cỡ kênh**: follower và mức thường.
- **Công thức đã thắng trên chính kênh**: điểm chung của các video vượt hẳn mức thường (kiểu tiêu đề, loại nội dung). Ghi kèm lượt xem.
- **Vai**: đoán từ caption (kể việc mình làm, giải nghĩa khái niệm, hay nói về quyết định), rồi xác nhận lại với người dùng trong một câu.
- **Câu hỏi kiểm tra**: một câu có/không rút từ khán giả và vai. Ví dụ với kênh dạy thao tác cho người đi làm: "Người xem có làm theo được trong 10–15 phút, không cần biết code không?"

Khi người dùng có nhiều kênh cùng khán giả, phải tách vai cho chúng (ví dụ một kênh "làm thế nào", một kênh "là gì và vì sao"), nếu không hai kênh sẽ nhận cùng ý tưởng. Nói rõ cách bạn tách và hỏi họ có đồng ý không.

Ghi kết quả vào `config/kenh.md`, thay hết các chỗ CHƯA ĐIỀN. Mỗi kênh một tiêu đề đúng dạng:

```
### 1. Tên đầy đủ (`Tên ngắn`) — @handle
```

Tên ngắn trong dấu `...` là thứ hiện trên báo cáo và phải trùng với trường `channel` trong `analysis.json`.

Nếu thấy nội dung kênh lệch với khán giả họ nêu (ví dụ kênh nói là cho nhà quản lý nhưng video toàn hướng dẫn thao tác), nói thẳng kèm số liệu. Đó là thông tin có ích.

## 3. Kênh mẫu

Danh sách theo dõi mẫu đã có sẵn các hãng AI, nhà sáng tạo quốc tế, báo chí và một số kênh Việt. Với các kênh người dùng nói muốn học theo:

1. Chạy `viral.py check tiktok <handle…>`.
2. Báo kết quả theo 5 điều kiện trong `kenh.md`. Lệnh đo điều kiện 2, 3, 4. Điều kiện 1 (đúng ngách) bạn xét qua caption. Điều kiện 5 (một người làm lại được) người dùng tự xét.
3. Thêm kênh đạt chuẩn vào `config/tiktok/watchlist.json`: kênh Việt chuyên AI vào nhóm "Kênh Việt chuyên AI"; kênh Việt nói nhiều chủ đề vào nhóm có `filter: keyword`. Kênh không đạt thì nói lý do bằng số và không thêm, trừ khi người dùng vẫn muốn.

### Tìm handle khi người dùng chỉ nhớ tên kênh

- Đừng đoán handle. Tỷ lệ trúng rất thấp.
- Nếu có công cụ tìm kiếm web: tìm tên kênh, giới hạn trong tiktok.com, lấy handle từ đường link video trong kết quả. Tìm theo cụm chủ đề tiếng Việt cũng ra thêm kênh cùng ngách.
- Không có công cụ tìm kiếm: nhờ người dùng mở TikTok, tìm kênh, chép tên sau dấu @.
- Phần lớn kênh tìm được sẽ trượt chuẩn (ngừng đăng, lượt xem thấp). Chuyện đó bình thường, cứ báo đúng số.

## 4. Quét lần đầu

Chạy quy trình quét trong SKILL.md. Trước khi quét, báo người dùng: mất khoảng 5–15 phút, kết quả là mỗi kênh mấy ý tưởng.

Lần quét đầu chưa có lịch sử nên chưa có tín hiệu "đang tăng tốc". Từ lần thứ hai trở đi mới có.

## Khi mạng bị chặn

Nếu gần như mọi tài khoản đều "không lấy được" ngay lần đầu, môi trường đang chặn mạng tới nguồn dữ liệu. Skill cần truy cập api.fxtwitter.com, www.tiktok.com và hn.algolia.com. Nói với người dùng: skill này chạy tốt trong Claude Code hoặc Cowork trên máy của họ; trong môi trường đám mây cần cho phép ba địa chỉ trên.
