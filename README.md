# Diagram Design (Thai Edition for Desktop AI Agents)

Skill นี้เป็นชุดคำสั่งสำหรับ AI Agent แบบ Desktop เพื่อสร้างแผนภาพ (Diagram) ออกมาเป็นไฟล์ HTML พร้อม SVG ในตัวแบบครบจบในที่เดียว รองรับแผนภาพถึง 44 รูปแบบ

## 📌 ที่มาและการดัดแปลง
Skill นี้ได้รับการดัดแปลงมาจากต้นฉบับ: [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) 

โดยเวอร์ชันนี้มีการปรับปรุงและเพิ่มประสิทธิภาพให้เหมาะสมกับการใช้งานดังต่อไปนี้:
- **รองรับ AI Agent แบบ Desktop**: ปรับแต่งให้ใช้งานร่วมกับ Desktop AI Agents ได้อย่างราบรื่น
- **รองรับภาษาไทยอย่างสมบูรณ์ (Thai-first)**: 
  - ใช้ฟอนต์มาตรฐานของ Windows ("Segoe UI Variable" และ "Leelawadee UI")
  - จัดการกฎเกณฑ์การจัดเรียงข้อความภาษาไทยเพื่อป้องกันปัญหาวรรณยุกต์ลอย
  - ปรับขนาดกล่องข้อความ, ระยะบรรทัด, และ Mask ให้เหมาะสมกับภาษาไทย
- **เพิ่มฟีเจอร์การ Export**: รองรับการสร้างไฟล์รูปภาพ `.png` โดยอัตโนมัติ และสามารถ Export เป็นไฟล์ `.drawio` ที่นำไปแก้ไขต่อได้ตามคำขอของผู้ใช้

## 🔄 การอัปเดตตามต้นฉบับ (Sync Upstream v2.6.74)
- **เพิ่ม 2 รูปแบบ Diagram ใหม่ (รวมเป็น 44 รูปแบบ)**:
  - `Axonometric Plan` (`references/type-axonometric-plan.md`): แผนผังมุมมองสามมิติแบบ 30° / 30° สำหรับพื้นที่, อาคาร, สำนักงาน, คลังสินค้า และ Floor plan
  - `Exploded Axonometric` (`references/type-exploded.md`): ภาพระเบิดชิ้นส่วนแบบสามมิติ แสดงโครงสร้างภายใน, Teardown อุปกรณ์, ลำดับการประกอบ และ Multi-layer AI/Tech Stack
- **ปรับปรุงระบบตรวจสอบความถูกต้อง (Verifiers & Parsers)**:
  - `verify_geometry.py`: ตรวจสอบการเดินเส้นเชื่อมโยง (Connector routing), จุดเชื่อมต่อห่างจากมุมกล่อง, ตรวจจับเส้นทับซ้อน พร้อมรักษา Mask Height สำหรับภาษาไทย
  - `self_check.py`: ตรวจจับ SVG naming ID ซ้ำ (`title`/`desc`) และรองรับ Flag `--offline` สำหรับตรวจสอบฟอนต์
  - `drawio_extract.py`: จำกัดขนาดโครงสร้าง XML, ป้องกันเซลล์เกินขีดจำกัด และคำนวณพิกัดอย่างปลอดภัย
  - `mermaid_extract.py` & `excalidraw_extract.py`: รองรับ State descriptions และป้องกัน ID ซ้ำ
  - `export_svg.py`: ปรับปรุงการฝัง CSS และรองรับโหมด `--system-fonts`
- **ปรับปรุงแนวทางฟอนต์และ Contrast**:
  - รองรับโหมด System Font / Offline เพื่อใช้งานโดยไม่ต้องเชื่อมต่อ Google Fonts
  - เพิ่มเติมกฎ Contrast WCAG 4.5:1 และ Semantic Token Placeholders

## 🚀 วิธีการใช้งานและการติดตั้ง
สามารถอ่านรายละเอียดโครงสร้างของ Diagram ทั้ง 44 รูปแบบ กฎเกณฑ์การออกแบบ และวิธีใช้งานเพิ่มเติมได้ในไฟล์ `SKILL.md` และโฟลเดอร์ `references/` ที่แนบมาในโปรเจกต์นี้
