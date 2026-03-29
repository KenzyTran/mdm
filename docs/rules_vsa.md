# BỘ QUY TẮC CHIẾN LƯỢC BREAKOUT KHỐI LƯỢNG ĐỘT BIẾN (VSA) - LONG ONLY

## I. ĐỊNH NGHĨA VÀ BIẾN SỐ ĐẦU VÀO

### 1. Dữ liệu đầu vào:
*   **Vũ trụ cổ phiếu:** Nhóm VN30.
*   **Dữ liệu giá:** Mở cửa ($O$), Cao nhất ($H$), Thấp nhất ($L$), Đóng cửa ($C$).
*   **Dữ liệu Khối lượng ($V$).**

### 2. Khối lượng trung bình ($MAV_{20}$):
*   Trung bình trượt đơn giản (SMA) của khối lượng 20 phiên:
    $$MAV_{20} = \frac{\sum_{i=1}^{20} V_i}{20}$$

### 3. Điều kiện Khối lượng đột biến (Volume Spike):
*   Một phiên được xác nhận là đột biến nếu:
    $$V \ge 4 \times MAV_{20}$$
    *(Lưu ý: Nếu VN30 quá ít tín hiệu, có thể điều chỉnh hệ số xuống 2.5x hoặc 3.0x).*

## II. TRẠNG THÁI 1: TÌM KIẾM TÍN HIỆU MUA (SCANNING)
**Trạng thái:** Đang cầm tiền mặt hoặc danh mục chưa đủ 5 mã.

### 1. Điều kiện xác nhận Điểm mua (Breakout):
Tín hiệu mua được kích hoạt khi thỏa mãn đồng thời:
*   **Điều kiện 1 (Lookback 5 ngày):** Trong 5 phiên gần nhất ($t-1$ đến $t-5$), có ít nhất một phiên thỏa mãn $V \ge 4 \times MAV_{20}$.
*   **Điều kiện 2 (Vượt đỉnh nến Spike):** Giá cao nhất phiên hiện tại ($H_t$) phải lớn hơn giá cao nhất của phiên có khối lượng đột biến đó ($H_{spike\_day}$).

### 2. Thực hiện lệnh Mua:
*   **Giá mua ($P_{buy}$):** Giá đóng cửa ($C$) của phiên hiện tại.
*   **Quy mô danh mục:** Tối đa 5 mã.
*   **Tỷ trọng:** 
    *   **Mặc định ban đầu:** 15% NAV cho mỗi mã
    *   **Tùy chọn nâng cao:** Sử dụng Kelly Criterion động (xem Mục VI) - tỷ trọng sẽ thay đổi từ 15% → 19-25% tùy theo hiệu suất giao dịch
*   **Ưu tiên:** Nếu nhiều mã báo mua cùng lúc, chọn mã có tỷ lệ $V / MAV_{20}$ cao nhất.

## III. TRẠNG THÁI 2: QUẢN TRỊ VỊ THẾ (HOLDING)
**Trạng thái:** Đang nắm giữ cổ phiếu.

### 1. Quy tắc Cắt lỗ (Stop Loss):
Bán toàn bộ vị thế nếu vi phạm 1 trong 2 điều kiện:
*   **Cắt lỗ cố định:** Giá đóng cửa giảm 7% từ điểm mua ($C_t \le P_{buy} \times 0.93$).
*   **Thủng đáy nến Spike:** Giá đóng cửa thấp hơn giá thấp nhất ($L$) của nến đột biến khối lượng dùng để xác nhận lệnh mua.

### 2. Quy tắc Bán theo Thời gian & Xu hướng (Time-Based Exit):
*   **Giai đoạn quan sát (7 tuần đầu - 35 phiên):**
    *   Theo dõi biến động giá so với đường MA10.
    *   Nếu trong suốt 7 tuần giá **KHÔNG BAO GIỜ** đóng cửa dưới MA10 $\rightarrow$ Sử dụng **MA10** làm đường trailing stop (điểm bán).
    *   Nếu có **bất kỳ phiên nào** giá đóng cửa dưới MA10 $\rightarrow$ Chuyển sang sử dụng **MA50** làm đường trailing stop (điểm bán) vĩnh viễn cho vị thế này.
*   **Sau 7 tuần:**
    *   Tiếp tục sử dụng đường trailing stop đã được xác định ở giai đoạn trước (MA10 hoặc MA50).
    *   Bán toàn bộ khi giá đóng cửa cắt xuống dưới đường trailing stop đang sử dụng.

### 3. Quy tắc Chốt lời mục tiêu (Take Profit):
*   Chốt lời chủ động 50% khối lượng khi lợi nhuận đạt 20%. Phần còn lại giữ theo Trailing Stop.

## IV. TRẠNG THÁI 3: TÍN HIỆU BÁN CƯỠNG BỨC (EXIT)
Bán ngay lập tức bất kể các quy tắc quản trị rủi ro nếu xuất hiện dấu hiệu phân phối.

### 1. Tín hiệu Phân phối Đột biến:
*   **Điều kiện:** Giá đóng cửa giảm ($C_t < C_{t-1}$) kèm khối lượng $V \ge 4 \times MAV_{20}$.
*   **Hành động:** Bán toàn bộ vị thế tại giá đóng cửa phiên đó.

## V. THÔNG SỐ CÀI ĐẶT BACKTEST (SUMMARY)

| Thông số | Giá trị thiết lập |
| :--- | :--- |
| **Vũ trụ** | VN30 |
| **Số lượng mã tối đa** | 5 mã |
| **Tỷ trọng mỗi mã** | 20% NAV (Cố định) hoặc Kelly Criterion (Động) |
| **Hệ số Volume Spike** | 4.0x (Baseline) |
| **Cửa sổ Lookback** | 5 phiên |
| **Stop Loss** | -7% / Thủng đáy Spike |
| **Trailing Stop** | MA10 (nếu tôn trọng 7 tuần đầu) / MA50 (nếu vi phạm) |
| **Loại lệnh** | Giá đóng cửa (Market on Close) |

---

## VI. CHIẾN LƯỢC PHÂN BỔ VỊ THẾ ĐỘNG - KELLY CRITERION (ROLLING KELLY)

### 1. Nguyên tắc

Tính Kelly dựa trên **30-50 giao dịch gần nhất**, không phải toàn bộ lịch sử. Điều này giúp thích ứng nhanh với thay đổi thị trường.

**Công thức Kelly:**
$$f^* = p - \frac{1-p}{R}$$

Trong đó:
*   $p$ = Win Rate (Tỷ lệ thắng)
*   $R$ = Avg Win / Avg Loss
*   Sử dụng **Half Kelly** = $f^*/2$ để giảm rủi ro

---

### 2. Quy trình triển khai

**Giao dịch 1-20:** Dùng **15% cố định** (vì chưa đủ dữ liệu)

**Giao dịch 21-50:** Tính Kelly từ **20 trade gần nhất**

**Giao dịch 51+:** Tính Kelly từ **50 trade gần nhất**, cập nhật liên tục sau mỗi giao dịch đóng

---

### 3. Ví dụ cụ thể

**Ví dụ 1: Sau 30 trade**

Lịch sử: 15 thắng, 15 thua
*   Win Rate = 50%
*   Avg Win = 22%, Avg Loss = 5%
*   R = 22/5 = 4.4
*   Kelly = 0.50 - (0.50/4.4) = 0.386 = **38.6%**
*   **Half Kelly = 19.3%** → Dùng **19%** cho trade thứ 31

**Ví dụ 2: Sau 60 trade (tính từ trade 11-60)**

Lịch sử 50 trade gần nhất: 24 thắng, 26 thua
*   Win Rate = 48%
*   Avg Win = 24%, Avg Loss = 5%
*   R = 24/5 = 4.8
*   Kelly = 0.48 - (0.52/4.8) = 0.372 = **37.2%**
*   **Half Kelly = 18.6%** → Dùng **18.6%** cho trade thứ 61

---

### 4. Quy tắc bảo vệ

*   **Tỷ trọng tối đa:** 25% NAV (ngay cả khi Kelly > 25%)
*   **Tỷ trọng tối thiểu:** 5% NAV
*   **Làm tròn:** Làm tròn đến bội số 1% hoặc 5% để đơn giản hóa
