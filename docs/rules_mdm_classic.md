# BỘ QUY TẮC MÔ HÌNH DỰ BÁO THỊ TRƯỜNG (MDM) - PHIÊN BẢN CHÍNH THỨC

## I. ĐỊNH NGHĨA VÀ BIẾN SỐ ĐẦU VÀO
**1. Dữ liệu đầu vào:**
* Giá Mở cửa ($O$), Cao nhất ($H$), Thấp nhất ($L$), Đóng cửa ($C$), Khối lượng ($V$).
* Dữ liệu chỉ số VNINDEX.

**2. Vị thế khung giá ($P_{loc}$):**
Công thức xác định vị trí giá đóng cửa trong thanh giá:
$$P_{loc} = \frac{C - L}{H - L}$$

**3. Ngày phân phối (Distribution Day - DD):**
* **Bộ đếm ($Count_{DD}$):** Tính tổng số ngày phân phối trong cửa sổ trượt 20 phiên giao dịch gần nhất.
* **Cơ chế Reset:** Ngay khi xuất hiện **Tín hiệu Mua** (FTD), đặt $Count_{DD} = 0$.

---

## II. TRẠNG THÁI 1: TÌM KIẾM CƠ HỘI (CASH / WAITING)
*Trạng thái hiện tại: 100% Tiền mặt.*

**1. Điều kiện xác nhận "Giai đoạn điều chỉnh":**
* Chỉ số VNINDEX giảm $\ge 10\%$ từ đỉnh cao nhất gần nhất.

**2. Điều kiện đếm "Ngày nỗ lực hồi phục" (Rally Attempt):**
* **Ngày 1 (Day 1):** Là ngày đầu tiên trong giai đoạn điều chỉnh thỏa mãn:
    * Giá đóng cửa tăng so với phiên trước ($C > C_{prev}$).
    * HOẶC: Giá giảm/tạo đáy mới nhưng đóng cửa ở nửa trên khung giá ($P_{loc} > 0.5$).
* **Quy tắc hủy đếm:** Nếu trong quá trình đếm, giá phá thủng đáy thấp nhất ($L$) của Ngày 1 $\rightarrow$ Hủy đếm, chờ thiết lập Ngày 1 mới.

**3. Tín hiệu Mua (Follow-Through Day - FTD):**
* **Thời gian:** Xuất hiện từ **Ngày thứ 3 đến Ngày thứ 11** của đợt nỗ lực hồi phục.
* **Điều kiện Giá:** Tăng mạnh $\ge 1\%$ so với phiên trước ($C \ge C_{prev} \times 1.01$).
* **Điều kiện Khối lượng:** Cao hơn phiên trước ($V > V_{prev}$).
* **Hành động:**
    * Chuyển trạng thái sang: **MUA (HOLDING)**.
    * Reset ngày phân phối: $Count_{DD} = 0$.
    * Ghi nhận **Giá Mua ($P_{buy}$)** = Giá đóng cửa phiên FTD.

**4. Tín hiệu Mua (Phá vỡ lên trên MA50 sau điều chỉnh):**
* **Điều kiện (tất cả phải thỏa mãn):**
    1. Sau giai đoạn điều chỉnh $\ge 6\%$ từ đỉnh.
    2. Phiên trước đóng cửa **dưới hoặc bằng** MA50 của phiên trước ($C_{prev} \le MA50_{prev}$).
    3. Phiên hiện tại đóng cửa **vượt lên trên** MA50 ($C > MA50$).
    4. Khối lượng cao hơn phiên trước ($V > V_{prev}$).
* **Hành động:**
    * Chuyển trạng thái sang: **MUA (HOLDING)**.
    * Reset ngày phân phối: $Count_{DD} = 0$.
    * Ghi nhận **Giá Mua ($P_{buy}$)** = Giá đóng cửa phiên phá vỡ MA50.

**5. Tín hiệu Mua (Vượt đỉnh 52 tuần):**
* **Điều kiện:** Chỉ số lần đầu vượt đỉnh 52 tuần.
* **Hành động:**
    * Giữ vị thế **MUA (HOLDING)**.
    * Đặt dừng lỗ là cách 1% so với mức thấp nhất của ngày hôm đó ($L \times 0.99$).

---

## III. TRẠNG THÁI 2: NẮM GIỮ (HOLDING / RISK MANAGEMENT)
*Trạng thái hiện tại: Đang nắm giữ cổ phiếu.*

**1. Quy tắc Cắt lỗ (Stop Loss):**
* **Điều kiện kích hoạt (1 trong 3):**
    1.  Giá trị chỉ số giảm **-1.5%** so với Giá Mua ($C < P_{buy} \times 0.985$).
    2.  Giá đóng cửa thấp hơn giá thấp nhất của ngày Tín hiệu Mua ($C < L_{buy}$).
    3.  Chỉ số **phá vỡ xuống dưới MA50** với khối lượng lớn hơn phiên trước:
        * Phiên trước đóng cửa **trên hoặc bằng** MA50 của phiên trước ($C_{prev} \ge MA50_{prev}$).
        * Phiên hiện tại đóng cửa **dưới** MA50 ($C < MA50$).
        * Khối lượng cao hơn phiên trước ($V > V_{prev}$).
* **Hành động:** BÁN NGAY $\rightarrow$ Chuyển về trạng thái Tiền mặt.

**2. Quy tắc đếm Ngày phân phối (DD):**
*Lưu ý: Không tính nếu là ngày Đáo hạn Phái sinh.*
* **Loại 1 (Giảm mạnh):**
    * Giá giảm $\ge 0.2\%$ ($C \le C_{prev} \times 0.998$).
    * Khối lượng tăng ($V > V_{prev}$).
* **Loại 2 (Chững lại - Stalling):**
    * Giá tăng nhẹ $< 0.1\%$ (hoặc tham chiếu).
    * Khối lượng tăng ($V > V_{prev}$).
    * Đóng cửa ở 25% dưới khung giá ($P_{loc} \le 0.25$).

**3. Ngoại lệ đặc biệt:**
* Nếu ngay sau phiên Tín hiệu Mua, bộ đếm $Count_{DD}$ đạt 5 ngày (do lỗi cộng dồn):
    * **Vẫn giữ trạng thái MUA**.
    * Chỉ bán nếu vi phạm quy tắc Cắt lỗ (Mục III.1).

---

## IV. TRẠNG THÁI 3: CẢNH BÁO & BÁN KHỐNG (WARNING & SHORT SELLING)

**1. Chuyển sang tín hiệu "CHỜ BÁN":**
* **Điều kiện:** Tổng số ngày phân phối trong 20 phiên gần nhất đạt 5 ngày ($Count_{DD} == 5$).
* **Hành động:**
    * Chuyển trạng thái sang: **CHỜ BÁN**.
    * Ghi nhận **Giá cao nhất ngày DD5 ($H_{DD5}$)** để tính dừng lỗ sau này.

**2. Vô hiệu hóa "CHỜ BÁN" (Quay lại MUA):**
* Nếu giá đóng cửa vượt đỉnh cao nhất của ngày phân phối thứ 5 ($C > H_{DD5}$).
* HOẶC xuất hiện một Tín hiệu Mua (FTD) mới.

**3. Thực hiện lệnh "BÁN KHỐNG" (Open Short):**
* **Điều kiện (tất cả phải thỏa):** Đang ở trạng thái "CHỜ BÁN" và:
    * Phiên trước đóng cửa **trên hoặc bằng** MA10 của phiên trước ($C_{prev} \ge MA10_{prev}$).
    * Phiên hiện tại đóng cửa **dưới** MA10 ($C < MA10$).
    * Khối lượng cao hơn phiên trước ($V > V_{prev}$).
* **Hành động:** 
    * BÁN TOÀN BỘ vị thế Long (nếu có).
    * MỞ VỊ THẾ BÁN KHỐNG (Short).
    * Ghi nhận **Giá Bán ($P_{sell}$)** = Giá đóng cửa phiên kích hoạt.

**4. Quản trị vị thế Bán Khống:**
* **Dừng lỗ (Stop Loss):**
    * Cắt lỗ nếu giá vượt **1%** so với giá cao nhất ngày DD5 ($C > H_{DD5} \times 1.01$).
* **Cover (Mua lại) - 1 trong 2 điều kiện:**
    1. Khi xuất hiện **Ngày Tín hiệu Mua (FTD)**.
    2. Chỉ số **phá vỡ lên trên MA50** với khối lượng lớn hơn phiên trước:
        * Phiên trước đóng cửa **dưới hoặc bằng** MA50 của phiên trước ($C_{prev} \le MA50_{prev}$).
        * Phiên hiện tại đóng cửa **vượt lên trên** MA50 ($C > MA50$).
        * Khối lượng cao hơn phiên trước ($V > V_{prev}$) hoặc khối lượng vượt trung bình 50 phiên hơn 10% ($V > 1.1 \times MA50_{vol}$).