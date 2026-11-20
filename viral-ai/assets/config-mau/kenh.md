# Hồ sơ kênh và tiêu chí chọn

File này là bộ lọc chính. Mỗi lần quét, Claude đọc nó để quyết định ý tưởng nào hợp kênh nào.
Chỗ nào còn ghi CHƯA ĐIỀN thì skill sẽ hỏi bạn rồi điền giúp. Bạn cũng có thể tự sửa bất cứ lúc nào.

Số ý tưởng mỗi kênh mỗi lần quét: 3

## Kênh của tôi

Mỗi kênh một mục. Tên trong ngoặc `...` là tên ngắn sẽ hiện trên báo cáo. Có thể có 1 đến 5 kênh.

### 1. CHƯA ĐIỀN tên đầy đủ (`CHƯA ĐIỀN tên ngắn`) — @CHƯA ĐIỀN

- **Khán giả**: CHƯA ĐIỀN (ai xem, họ làm nghề gì, họ biết gì về AI)
- **Vai**: CHƯA ĐIỀN (người làm "tôi đã làm thế nào" / người giải thích "X là gì" / người ra quyết định / khác)
- **Cỡ kênh**: CHƯA ĐIỀN (skill tự đo từ TikTok)
- **Công thức đã thắng trên chính kênh**: CHƯA ĐIỀN (skill tự rút ra từ các video nhiều lượt xem nhất)
- **Câu hỏi kiểm tra**: CHƯA ĐIỀN (một câu hỏi có/không để biết ý tưởng có hợp kênh này không)

## Tiêu chí chọn kênh để học theo

Có hai loại nguồn, dùng khác nhau:

- **Kênh mẫu**: học cả chủ đề lẫn công thức trình bày. Phải qua đủ 5 điều kiện dưới đây.
- **Nguồn tin**: hãng AI, báo chí, tài khoản X của người trong ngành. Chỉ lấy chủ đề và số liệu, không học cách trình bày.

| # | Điều kiện | Ngưỡng | Vì sao |
|---|---|---|---|
| 1 | Đúng ngách | Từ 60% video cùng chủ đề với kênh của bạn | Kênh lạc đề cho ý tưởng không dùng được |
| 2 | Còn hoạt động | Từ 2 video mỗi tuần, video mới nhất trong 7 ngày | Kênh ngủ không cho tín hiệu hằng ngày |
| 3 | Thắng nhờ nội dung, lặp lại được | Trong 12 video gần nhất có từ 2 video gấp 3 lần mức thường của chính kênh đó | Một video trúng có thể là may. Hai video thì là công thức |
| 4 | Đủ lớn để đáng học | Video tốt nhất từ 20 nghìn lượt xem | Phải thắng rõ hơn kênh của mình thì mới có gì để học |
| 5 | Làm lại được | Một người, nói trước ống kính hoặc quay màn hình | Điều kiện này phải xem video mới biết |

Loại ngay: kênh đăng lại video người khác, kênh hứa kiếm tiền nhanh, kênh hãng có dấu hiệu chạy quảng cáo, kênh chỉ bán khoá học.

Số lượng nên có: mỗi kênh của bạn 10–15 kênh mẫu. Lệnh `viral.py check tiktok <tên kênh>` đo giúp điều kiện 2, 3, 4.

Kênh đã loại, đừng thêm lại: (chưa có)

## Tiêu chí chọn nội dung

### Vòng 1: điều kiện chung (trượt một điều là loại)

1. Thật sự về AI trong công việc hoặc kinh doanh.
2. Có bằng chứng thắng: gấp từ 3 lần mức thường của kênh gốc, hoặc thuộc hạng viral trở lên, hoặc còn mới và đang tăng nhanh. Tin lớn chưa viral vẫn được chọn nhưng phải nói rõ là chưa viral.
3. Một người làm xong trong một ngày, và tự thử lại được trước khi quay.
4. Chưa từng chọn, trừ khi có diễn biến mới.
5. Không thuộc mục "Tránh".

### Vòng 2: giao cho kênh

Dùng câu hỏi kiểm tra của từng kênh. Một nguồn chỉ giao cho một kênh. Nếu hợp nhiều kênh, giao cho kênh có điểm hợp cao hơn.

### Vòng 3: ba vai của ý tưởng

Mỗi ý tưởng mang một vai (trường `slot`). Cố gắng để mỗi kênh có đủ cả ba vai:

| `slot` | Nghĩa | Lấy từ đâu |
|---|---|---|
| `chac-thang` | Công thức đã được chứng minh với khán giả Việt | Video kênh Việt vượt mức thường, hoặc chủ đề trùng công thức đã thắng trên chính kênh |
| `di-truoc` | Đang thắng ở nước ngoài, kênh Việt được quét chưa ai làm | Nhà sáng tạo quốc tế, báo cáo X cùng ngày |
| `bat-tin` | Tin hoặc xu hướng trong 48 giờ, kể theo góc của kênh | Hãng AI, báo chí, X |

Khi thiếu ứng viên đạt vòng 1, lấp theo thứ tự: video trong 7 ngày → thêm một ý `chac-thang` → ứng viên điểm thấp hơn, xếp mức `theo-doi` và ghi rõ "chưa viral". Nếu vẫn thiếu, để thiếu và nói rõ. Không bịa cho đủ.

## Giọng

- Nói như người thật, câu ngắn, ví dụ đời thường. Không hô khẩu hiệu, không phóng đại.
- Luôn tự thử trước khi khuyên người khác dùng.

## Tránh

- Tin gọi vốn, chính trị, kiện tụng, chuyện đời tư, thuyết âm mưu.
- Nội dung quá kỹ thuật trừ khi có góc đời thường.
- Lời hứa kiếm tiền nhanh.
- Bài tự gắn mác BREAKING mà không có nguồn.

## Năng lực sản xuất

- Mỗi kênh đăng mấy video mỗi ngày, ai làm: CHƯA ĐIỀN
