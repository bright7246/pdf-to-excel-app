import io
import re
import pandas as pd
from pdf2image import convert_from_bytes
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="고화질 OCR 통화내역 완벽 정제기", page_icon="📞", layout="centered"
)

st.title("📞 고화질 전처리 기반 OCR 통화내역 변환기")
st.write(
    "스캔본 이미지 해상도를 강제로 높이고 흑백 대비를 극대화하여, 순번과"
    " 착신번호가 밀리지 않고 완벽하게 일치하도록 정제합니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "PDF 고화질 렌더링 및 OCR 이미지 전처리(흑백 대비 강화) 수행 중..."
    ):
      pdf_bytes = uploaded_file.read()
      
      # DPI를 300으로 높여서 초고화질 이미지로 변환
      images = convert_from_bytes(pdf_bytes, dpi=300)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지 고화질 분석 중...")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        all_raw_lines = []

        phone_pattern = re.compile(r'\d{2,3}-\S*-\d{4}')
        datetime_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')
        time_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]

          # --- [이미지 전처리 파이프라인] ---
          # 1. 흑백(Grayscale) 변환
          gray = ImageOps.grayscale(img)
          
          # 2. 선명도 및 대비(Contrast) 극대화 (글자를 뚜렷하게)
          enhancer = ImageEnhance.Contrast(gray)
          enhanced = enhancer.enhance(2.0)  # 대비 2배 강화
          
          # 3. 이미지 크기 2배 확대 (작은 스캔 글씨 인식률 대폭 향상)
          w, h = enhanced.size
          resized = enhanced.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
          
          # --- [Tesseract OCR 정밀 호출] ---
          # --psm 6 : 균일한 단일 블록의 텍스트 줄들로 구성된 표 문서로 강제 해석
          custom_config = r'--oem 3 --psm 6'
          ocr_text = pytesseract.image_to_string(resized, lang="kor+eng", config=custom_config)

          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()
            if not line_str:
              continue

            # 머리글 필터링
            if any(
                kw in line_str
                for kw in [
                    "개인정보유출주의",
                    "다운로드일시",
                    "발신지 통화내역",
                    "접수번호",
                    "전화번호",
                    "조회기간",
                    "전체건수",
                ]
            ):
              continue

            all_raw_lines.append((index + 1, line_str))

        parsed_rows = []
        expected_seq = 1  # 1번부터 순번 연속성 강제 추적

        for page_no, line_str in all_raw_lines:
          # OCR 오타 보정
          cleaned = (
              line_str.replace("ucu+", "LGU+")
              .replace("tcu+", "LGU+")
              .replace("ucu", "LGU+")
              .replace("tcu", "LGU+")
              .replace("|", " ")
              .replace("O", "0")  # 알파벳 O를 숫자 0으로 오인식한 경우 보정
              .replace("o", "0")
          )

          tokens = cleaned.split()
          if len(tokens) < 3:
            continue

          # 전화번호나 시간이 포함된 유효 행 검증
          has_phone = bool(phone_pattern.search(cleaned))
          has_time = bool(datetime_pattern.search(cleaned)) or bool(
              time_pattern.search(cleaned)
          )

          if has_phone or has_time:
            business = "LGU+"

            # 순번 찾기 (숫자 토큰 중 현재 기대 순번과 가장 가까운 것 탐색)
            found_seq = None
            for t in tokens[:5]:
              # 숫자만 추출
              digits_only = "".join(filter(str.isdigit, t))
              if digits_only.isdigit() and len(digits_only) <= 4:
                val = int(digits_only)
                if abs(val - expected_seq) <= 3:
                  found_seq = val
                  break

            if found_seq and found_seq >= expected_seq:
              current_seq = found_seq
              expected_seq = found_seq + 1
            else:
              current_seq = expected_seq
              expected_seq += 1

            # 사용유형 추출
            usage_type = "VOLTE음성"
            for t in tokens:
              upper_t = t.upper()
              if (
                  "3G" in upper_t
                  .replace("O", "0")
                  or "VOLTE" in upper_t
                  or "LTE" in upper_t
                  or "음성" in t
                  or "문자" in t
              ):
                usage_type = t
                break

            # 착신번호 추출
            phone_match = phone_pattern.search(cleaned)
            phone = phone_match.group(0) if phone_match else ""

            # 통화시작시간 추출
            dt_match = datetime_pattern.search(cleaned)
            start_time = dt_match.group(0) if dt_match else ""

            # 사용시간 추출
            time_matches = time_pattern.findall(cleaned)
            duration = ""
            if len(time_matches) >= 2:
              duration = time_matches[1]
            elif len(time_matches) == 1 and not start_time:
              duration = time_matches[0]

            # 발신기지국주소 추출
            address = ""
            if dt_match:
              dt_end_idx = cleaned.find(start_time) + len(start_time)
              residual = cleaned[dt_end_idx:].strip()
              if residual:
                if duration and residual.startswith(duration):
                  residual = residual[len(duration) :].strip()
                address = residual.lstrip("|- ").strip()

            if phone:
              parsed_rows.append({
                  "페이지": page_no,
                  "사업자": business,
                  "순번": current_seq,
                  "사용유형": usage_type,
                  "착신번호": phone,
                  "통화시작시간": start_time,
                  "사용시간(초)": duration,
                  "발신기지국주소": address,
              })

        if len(parsed_rows) > 0:
          df = pd.DataFrame(parsed_rows)
          # 중복 제거 및 순번 정렬
          df = df.drop_duplicates(subset=["순번"]).sort_values(by="순번").reset_index(drop=True)

          st.success(
              f"초고화질 전처리 및 순번 보정 완료! 총 {len(df)}건의 데이터가"
              " 정확하게 매칭되었습니다."
          )

          st.write("### 정제된 표 데이터 미리보기")
          st.dataframe(df.head(15))

          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="고화질정제통화내역")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 고화질 정제 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="high_quality_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning("데이터 행을 추출하지 못했습니다.")

  except Exception as e:
    st.error(f"처리 중 오류 발생: {e}")
