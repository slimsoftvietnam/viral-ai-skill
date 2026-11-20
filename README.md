# Viral AI — skill cho Claude

Mỗi ngày skill quét các bài và video về AI đang viral trên X và TikTok, rồi chọn ra vài ý tưởng video cho từng kênh TikTok của bạn, kèm báo cáo HTML. Bạn chỉ cần trò chuyện với Claude bằng tiếng Việt.

## Cài đặt

**Claude (ứng dụng máy tính hoặc web)**

1. Tải file [`viral-ai.skill`](viral-ai.skill).
2. Trong Claude, mở Cài đặt → Skills và tải file lên.
3. Mở cuộc trò chuyện mới, gõ: `cài viral-ai`.

**Claude Code**

Chép thư mục [`viral-ai/`](viral-ai) vào `.claude/skills/` của dự án, hoặc `~/.claude/skills/` để dùng ở mọi dự án. Rồi gõ `cài viral-ai`.

Máy cần có Python 3.10 trở lên. Skill chỉ dùng thư viện chuẩn, không phải cài thêm gì.

## Dùng thế nào

| Bạn gõ | Skill làm |
|---|---|
| `cài viral-ai` | Tạo thư mục làm việc, hỏi 3 câu về kênh của bạn, lập hồ sơ kênh |
| `quét viral AI hôm nay` | Quét X và TikTok, đưa bảng ý tưởng cho từng kênh và báo cáo |
| `kiểm tra kênh @tenkenh` | Đo kênh theo tiêu chí kênh mẫu, nói có nên theo dõi không |
| `thêm kênh …` / `bỏ kênh …` | Chỉnh danh sách kênh được quét |
| `tôi đang ở bước nào` | Báo trạng thái và việc nên làm tiếp |

Tài liệu đầy đủ có sơ đồ: mở [`viral-ai/assets/huong-dan.html`](viral-ai/assets/huong-dan.html) bằng trình duyệt.

## Cách hoạt động

1. **Máy làm phần số**: thu thập bài của khoảng 180 tài khoản X và 90 kênh TikTok, chấm điểm theo quy mô, mức vượt mức thường của tác giả, tốc độ tăng.
2. **Claude làm phần chữ**: lọc qua ba vòng (đáng làm không, hợp kênh nào, đóng vai gì), giải thích vì sao viral bằng số liệu, viết khung kịch bản.
3. **Báo cáo**: một trang HTML cho mỗi nền tảng, lọc được theo kênh.

## Nguồn dữ liệu

Mặc định dùng nguồn công khai, miễn phí, không cần đăng ký: FxTwitter cho X và trang nhúng hồ sơ công khai cho TikTok. Skill không vượt lớp chống bot và không dùng API nội bộ của nền tảng.

Giới hạn: TikTok chỉ thấy các kênh trong danh sách theo dõi và chỉ có lượt xem. Có thể bật thêm nguồn trả phí (twitterapi.io, Apify) bằng biến môi trường; xem [`viral-ai/references/nguon-du-phong.md`](viral-ai/references/nguon-du-phong.md). Hai nguồn trả phí này chưa được kiểm thử với key thật.

## Cấu trúc

```
viral-ai/
├── SKILL.md              Quy trình và nguyên tắc
├── scripts/              Bộ máy thu thập, chấm điểm, xuất báo cáo
├── assets/config-mau/    Hồ sơ kênh mẫu, danh sách theo dõi, ngưỡng chấm điểm
├── assets/huong-dan.html Tài liệu hướng dẫn có sơ đồ
└── references/           Thiết lập lần đầu, cách đọc tín hiệu, công thức điểm
```

Dữ liệu của bạn (hồ sơ kênh, kết quả quét, báo cáo) nằm trong thư mục làm việc riêng, tách khỏi skill, nên cập nhật skill không mất dữ liệu.
