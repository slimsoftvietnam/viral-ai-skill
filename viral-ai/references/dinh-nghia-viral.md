# Thế nào là nội dung viral

## Câu trả lời ngắn

X không công bố ngưỡng nào để gọi một bài là viral, và các công ty phân tích mỗi nơi đưa một con số khác nhau. Định nghĩa dùng được trong thực tế là:

> Một bài viral khi nó **lan ra ngoài tệp người theo dõi của tác giả với tốc độ bất thường**, do người xem chủ động chia sẻ chứ không do tác giả trả tiền.

Định nghĩa này có ba vế, và mỗi vế đo được:

| Vế | Câu hỏi | Đo bằng |
|---|---|---|
| Lan ra ngoài | Bài có tới được người lạ không? | Lượt xem so với số follower; số repost và quote |
| Bất thường | Bài có vượt mức thường của chính tác giả không? | Tương tác của bài so với trung vị các bài gần đây của họ |
| Tốc độ | Bài lan nhanh cỡ nào? | Lượt xem mỗi giờ |

Chỉ nhìn lượt xem là sai theo hai hướng. Bài của tài khoản 5 triệu follower đạt 500 nghìn lượt xem chỉ là một ngày bình thường. Ngược lại, bài quảng cáo có thể mua được vài triệu lượt xem mà không ai tương tác.

## Các nguồn tham khảo

**Con số thị trường (không chính thức).** Các bài tổng hợp năm 2026 thường đặt mốc viral trên X ở khoảng 500 nghìn đến 1 triệu lượt xem trong 2–3 ngày. Tỷ lệ tương tác trung vị trên X được báo cáo quanh 0,6–1,3% tuỳ cách tính, trên 3% là rất tốt. Các con số này lệch nhau vì mỗi nơi chia cho một mẫu số khác (lượt xem hoặc follower).

**Thuật toán của X.** Mã nguồn bảng tin "For You" được X công bố (kho `xai-org/x-algorithm`). Điểm xếp hạng là tổng có trọng số của xác suất người xem thực hiện từng hành động: thích, trả lời, repost, quote, chia sẻ qua tin nhắn, bấm vào, dừng lại đọc, xem video, theo dõi tác giả. Các hành động tiêu cực (không quan tâm, tắt tiếng, chặn, báo cáo) bị trừ điểm. Trọng số thật không nằm trong phần giới thiệu của kho mã, nên các con số kiểu "một repost bằng 20 lượt thích" lan truyền trên mạng chưa được xác minh. Điều chắc chắn là: hành động chia sẻ và thời gian dừng đọc quan trọng hơn lượt thích.

**Nghiên cứu học thuật.**

- Berger và Milkman (2012), *What Makes Online Content Viral?*, phân tích gần 7.000 bài của New York Times: nội dung gợi cảm xúc kích hoạt mạnh (kinh ngạc, tức giận, lo lắng) được chia sẻ nhiều hơn. Nội dung gây buồn, là cảm xúc làm người ta chùng xuống, được chia sẻ ít hơn. Kết quả vẫn đúng sau khi đã tính đến độ hữu ích và độ bất ngờ.
- Jonah Berger, sách *Contagious*, khung STEPPS gồm sáu yếu tố: vốn xã hội (chia sẻ để trông sành), tác nhân gợi nhớ, cảm xúc, tính công khai, giá trị thực dụng, câu chuyện.
- Goel và cộng sự (2016) phân biệt hai kiểu lan: **phát sóng** (một tài khoản lớn đăng, rất nhiều người thấy trực tiếp) và **lây lan** (truyền qua nhiều tầng người chia sẻ). Một bài có thể rất nhiều lượt xem mà không hề lây lan. Đó là lý do hệ thống này đo độ vượt trội và tỷ lệ chia sẻ chứ không chỉ đo quy mô.

## Hệ thống này chấm điểm thế nào trên X

Điểm viral từ 0 đến 100, gồm bốn phần:

| Phần | Tỷ trọng | Cách tính |
|---|---|---|
| Quy mô | 30% | Lượt xem, thang log từ 30 nghìn (0 điểm) đến 10 triệu (100 điểm) |
| Độ vượt trội | 30% | Tương tác có trọng số của bài chia cho trung vị các bài gốc cũ hơn 12 giờ của cùng tác giả. Gấp 1 lần là 0 điểm, gấp 10 lần là 100 điểm. Nếu không có lịch sử tác giả thì dùng lượt xem chia follower |
| Tốc độ | 20% | Lượt xem mỗi giờ, thang log từ 2 nghìn đến 300 nghìn |
| Chất lượng tương tác | 20% | Tỷ lệ tương tác trên lượt xem (60%), tỷ lệ chia sẻ (25%), tỷ lệ lưu (15%) |

Tương tác có trọng số = thích × 1 + trả lời × 2 + lưu × 2 + repost × 3 + quote × 4.
Đây là trọng số do hệ thống tự đặt theo thứ tự ưu tiên của thuật toán X (chia sẻ nặng hơn thích), không phải con số của X.

Cộng thêm tối đa 9 điểm nếu bài được các tài khoản trong danh sách theo dõi repost hoặc quote (3 điểm mỗi tài khoản).

Trừ điểm nếu tỷ lệ tương tác dưới 0,4%. Dưới 0,2% và trên 100 nghìn lượt xem thì gắn nhãn nghi chạy quảng cáo.

## Năm hạng

| Hạng | Điều kiện |
|---|---|
| Siêu viral | Từ 1 triệu lượt xem trong cửa sổ quét |
| Viral | Từ 250 nghìn lượt xem và (gấp 3 lần mức thường hoặc tỷ lệ tương tác từ 2%). Hoặc gấp 5 lần mức thường với từ 100 nghìn lượt xem |
| Bứt phá | Gấp 3 lần mức thường, từ 50 nghìn lượt xem. Viral trong ngách |
| Đang lên | Đăng chưa quá 12 giờ, từ 15 nghìn lượt xem mỗi giờ |
| Đáng chú ý | Qua ngưỡng tối thiểu (30 nghìn lượt xem hoặc 300 lượt thích) nhưng chưa đạt các mức trên |

Mọi ngưỡng đều sửa được trong `config/x/settings.json`.

## Đọc "chữ ký" của một bài viral

Tỷ lệ giữa các loại tương tác cho biết bài viral theo kiểu nào, và từ đó nên làm lại theo định dạng nào:

| Chữ ký | Nghĩa là | Nên làm thành |
|---|---|---|
| Lưu ≥ 45% số thích | Người xem muốn dùng lại | Video hướng dẫn, kêu gọi lưu |
| Trả lời ≥ 25% số thích | Người xem chia phe | Video nêu quan điểm |
| Quote ≥ 50% số repost | Ai cũng muốn thêm ý kiến | Video phản ứng |
| Chia sẻ ≥ 20% số thích | Tin đáng báo cho người khác | Tin nhanh |
| Lượt xem ≥ 3 lần follower | Đã lan ra người lạ | Ý tưởng có sức tự thân |

## TikTok: cùng định nghĩa, khác phép đo

Định nghĩa ở đầu trang vẫn đúng cho TikTok, nhưng cách đo phải đổi vì hai lý do.

**Thuật toán khác.** Theo bài giải thích của chính TikTok về bảng tin For You, video được phân phối dựa trên phản ứng của người xem (xem hết, xem lại, chia sẻ, bình luận, theo dõi) và thông tin của video, còn số follower của tác giả không phải yếu tố trực tiếp. Hệ quả: trên TikTok, một tài khoản vài nghìn follower vẫn có thể đạt hàng triệu lượt xem, và một tài khoản lớn vẫn có video chỉ vài nghìn lượt. Lượt xem tuyệt đối vì thế nói ít hơn nữa so với trên X. Phép đo đáng tin nhất là **video đó gấp mấy lần mức thường của chính kênh**.

**Dữ liệu khác.** Nguồn miễn phí của TikTok chỉ cho lượt xem. Không có thích, bình luận, chia sẻ, lưu.

**Con số thị trường (không chính thức).** Các bài tổng hợp năm 2026 thường gọi 1 triệu lượt xem là viral trên TikTok, 100–250 nghìn là viral trong ngách, và nhấn mạnh tính tương đối: kênh thường đạt 500 lượt xem mà có video 50 nghìn thì đó là viral với kênh ấy. Các nguồn này cũng cho rằng tỷ lệ xem hết, lượt chia sẻ và lượt lưu hiện nặng hơn lượt thích. TikTok chưa công bố con số nào, nên hãy coi đây là ước lượng của giới làm nghề.

### Điểm viral trên TikTok

| Phần | Tỷ trọng | Cách tính |
|---|---|---|
| Quy mô | 30% | Lượt xem, thang log từ 20 nghìn đến 10 triệu |
| Độ vượt trội | 30% | Lượt xem chia cho trung vị lượt xem các video khác của kênh (không tính video ghim, chỉ tính video đăng hơn một ngày). Gấp 10 lần là 100 điểm |
| Tốc độ | 20% | Lượt xem mỗi giờ, thang log từ 1 nghìn đến 200 nghìn |
| Lan ngoài tệp | 20% | Lượt xem chia follower, thang log từ 0,2 đến 10. Nếu bật nguồn có số tương tác thì phần này đổi thành chất lượng tương tác |

Hạng dùng cùng tên với X: siêu viral từ 1 triệu lượt xem; viral từ 250 nghìn và gấp 3 lần mức thường; bứt phá gấp 3 lần mức thường từ 30 nghìn; đang lên khi chưa quá 12 giờ và từ 10 nghìn lượt mỗi giờ.

### Ba điều riêng của TikTok

- **Lên chậm.** Thuật toán thử video trên nhóm nhỏ rồi mở rộng dần, đỉnh thường đến sau 3–7 ngày. Ngoài cửa sổ 48 giờ, hệ thống đưa thêm tối đa 12 video trong 7 ngày vẫn gấp từ 3 lần mức thường.
- **Quảng cáo khó lọc.** Tài khoản hãng thường trả tiền đẩy video (Spark Ads). Không có số tương tác thì không kiểm chứng được, nên video của tài khoản hãng gấp từ 15 lần mức thường bị gắn nhãn nghi chạy quảng cáo và trừ 40% điểm. Lượt xem của tài khoản hãng nói chung nên được đọc với sự nghi ngờ.
- **Kênh Việt có ngưỡng riêng.** Kênh Việt nhỏ hơn kênh quốc tế nhiều, nên ngưỡng lọt vòng là 5 nghìn lượt xem thay vì 20 nghìn.

Mọi ngưỡng nằm trong `config/tiktok/settings.json`.

## Giới hạn cần biết

- Trên TikTok, hệ thống chỉ thấy 12 video mới nhất của các tài khoản trong danh sách, chỉ có lượt xem, và chỉ đọc được caption. Video viral của người lạ sẽ bị sót.
- Lượt xem trên X được tính rất dễ dãi (bài lướt qua màn hình cũng tính), nên luôn đọc cùng tỷ lệ tương tác.
- Hệ thống chỉ thấy bài của khoảng 170 tài khoản trong danh sách, bài họ chia sẻ lại, và bài bắt được qua 25 truy vấn tìm kiếm. Một bài viral của người lạ, không dùng từ khoá nào trong danh sách và không được KOL nào chia sẻ, sẽ bị sót.
- Nguồn dữ liệu là dịch vụ miễn phí của bên thứ ba, có thể chậm hoặc ngừng bất cứ lúc nào.
- Điểm số đo độ lan truyền, không đo độ đúng. Bài sai sự thật vẫn có thể rất viral.

## Nguồn

- [Kho mã thuật toán của X](https://github.com/xai-org/x-algorithm)
- [Berger & Milkman, What Makes Online Content Viral?](https://faculty.wharton.upenn.edu/wp-content/uploads/2011/11/Virality.pdf)
- [Scientific American, What Makes Content Go Viral](https://www.scientificamerican.com/article/the-secret-to-online-success-what-makes-content-go-viral/)
- [Ordinal, nghiên cứu tương tác trên X](https://www.tryordinal.com/blog/twitter-x-engagement-data-study)
- [Learning Revolution, How Many Views Is Viral](https://www.learningrevolution.net/how-many-views-is-viral/)
- [Tài liệu FxTwitter API](https://docs.fxembed.com/api/twitter/)
- [TikTok, How TikTok recommends videos #ForYou](https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you)
- [Toptal, How to go viral on TikTok](https://www.toptal.com/creator/post/how-to-go-viral-on-tiktok)
