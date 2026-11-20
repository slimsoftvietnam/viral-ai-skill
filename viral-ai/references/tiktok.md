# Nền tảng TikTok

## Nguồn dữ liệu và giới hạn

Trang nhúng hồ sơ công khai của TikTok (`tiktok.com/embed/@handle`), miễn phí, không cần key. Mỗi tài khoản trả về 12 video mới nhất kèm lượt xem và số follower. Thời điểm đăng được giải mã từ ID video.

Ba giới hạn phải nhớ suốt quá trình biên tập:

1. **Chỉ có lượt xem.** Không có thích, bình luận, chia sẻ, lưu (các trường này là `null`). Vì vậy không đo được chất lượng tương tác và không lọc chắc được video chạy quảng cáo.
2. **Chỉ thấy tài khoản trong danh sách.** Video viral của người lạ sẽ bị sót. Mọi nhận định kiểu "chưa ai làm" chỉ đúng trong phạm vi các kênh được quét, phải ghi rõ như vậy.
3. **Chỉ có caption.** Bạn không xem được video. Mọi kịch bản là khung, mọi `risk` phải nhắc người dùng xem video gốc.

Không dùng trang video, API nội bộ hay bất cứ thứ gì phải vượt lớp chống bot của TikTok. Nguồn tuỳ chọn có token (Apify) bổ sung số tương tác, xem `nguon-du-phong.md`.

## Bước 1: đọc bảng tóm tắt

Thu thập mất khoảng 2–3 phút.

- Tài khoản báo `lỗi(400)`: handle không tồn tại. Báo `không có video công khai`: tài khoản có nhưng không cho nhúng hoặc chưa đăng gì. Báo người dùng để sửa `watchlist.json`.
- Dòng "Tài khoản được nhắc nhiều, chưa có trong danh sách": gợi ý cho người dùng thêm vào danh sách.
- Dấu `*` ở cột loại: video đăng trước cửa sổ 48 giờ nhưng còn nóng trong tuần (trường `late` là true).

## Các rổ ứng viên (`origin`)

| Giá trị | Nghĩa | Cách dùng |
|---|---|---|
| `brand` | Tài khoản hãng | Nguồn tin ra mắt. Lượt xem có thể được mua, đọc với sự nghi ngờ |
| `creator` | Nhà sáng tạo và báo chí quốc tế | Nguồn ý tưởng để Việt hoá |
| `vn` | Kênh Việt | Tín hiệu trực tiếp từ thị trường. Không Việt hoá, mà học công thức rồi làm bản của mình cho khán giả khác hoặc góc khác |
| `discovery` | Tìm qua hashtag (chỉ khi bật nguồn có token) | Có đủ số tương tác |

## Vì sao có video ngoài 48 giờ

TikTok đẩy video chậm hơn X. Thuật toán thử video trên từng nhóm nhỏ rồi mở rộng dần, nên đỉnh thường đến sau 3–7 ngày. Một kênh nhỏ hiếm khi đạt lượt xem cao trong 48 giờ đầu. Vì vậy bộ thu thập đưa thêm tối đa 12 video đăng trong 7 ngày vẫn gấp từ 3 lần mức thường của kênh, gắn nhãn `ngoai-cua-so`.

Cách dùng: video trong 48 giờ ưu tiên cho `lam-ngay`. Video `late` hợp với `nen-lam` vì công thức của chúng đã được chứng minh, và phải ghi tuổi video trong `risk` hoặc `deadline`.

## Đọc tín hiệu

Phép đo quan trọng nhất là `outlier_ratio`: lượt xem của video chia cho trung vị lượt xem các video khác của cùng kênh (`baseline_median_views`). Nó cho biết nội dung thắng chứ không phải kênh thắng.

| Dấu hiệu | Ý nghĩa | Gợi ý |
|---|---|---|
| `outlier_ratio` từ 3 trở lên | Vượt mức thường của kênh | Đáng xem công thức |
| `vuot-xa-muc-thuong` (từ 5 lần) | Thắng lớn | Tìm xem caption, chủ đề, định dạng khác gì các video còn lại của kênh |
| `tk-nho-bung-no` | Dưới 50 nghìn follower mà đạt từ 250 nghìn lượt xem | Công thức tự thân mạnh nhất, đáng học nhất |
| `vuot-tep-follower` | Lượt xem gấp đôi follower trở lên | Đã lên For You của người lạ |
| `dang-tang-toc` | Tốc độ từ lần quét trước cao hơn tốc độ trung bình | Thuật toán đang đẩy, cửa sổ còn mở |
| `con-moi` + lượt xem mỗi giờ cao | Tín hiệu sớm | Làm ngay nếu hợp kênh |
| `nghi-quang-cao` | Tài khoản hãng gấp từ 15 lần mức thường | Gần như chắc là quảng cáo trả tiền. Chỉ chọn nếu nội dung tự nó có giá trị |
| `outlier_ratio` quanh 1 | Mức thường | Không viral. Nếu vẫn chọn (tin lớn), nói thẳng là chưa viral |
| `duoc-ghim` | Hãng chủ động đẩy | Không phải tín hiệu viral |

Với tài khoản hãng, hãy so các video trong cùng đợt với nhau: video nào trong loạt vượt hẳn lên thì cách kể của video đó đáng học (ví dụ video dùng bằng chứng người thật thắng video giới thiệu tính năng).

## Trường `format_lesson`

Với TikTok, mỗi ý tưởng nên có `format_lesson`: công thức trình bày đáng học, suy ra từ thứ bạn thật sự thấy (cấu trúc caption, cách đặt con số, loạt video nào thắng trong cùng đợt). Không suy đoán về hình ảnh hay cách dựng mà bạn chưa xem.

## Đối chiếu với X

Nếu trong ngày đã có `data/x/<ngày>/candidates.json`, mở ra để tìm:

- Chủ đề nóng trên X mà TikTok chưa ai làm hoặc video hãng chỉ ở mức thường: cơ hội đi trước. Ghi nguồn con số là "theo báo cáo X cùng ngày".
- Chủ đề xuất hiện ở cả hai nơi: ưu tiên cao hơn.

## Bẫy riêng

- Trong tiếng Việt "ai" viết thường nghĩa là "người nào". Bộ lọc đã xử lý với kênh Việt, nhưng vẫn kiểm tra lại video của nhóm `vn` có thật về AI không.
- Lượt xem do TikTok làm tròn (ví dụ 1,9 triệu), đừng viết như số chính xác tới hàng đơn vị.
- Kênh báo chí đăng rất dày, mức thường tính trên các video mới vài giờ nên có thể thấp. `outlier_ratio` hàng trăm lần ở kênh báo chí vẫn là tín hiệu thật, nhưng hãy nêu cả con số tuyệt đối.
