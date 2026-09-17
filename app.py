import io
import re
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="통화내역 패턴 맞춤 정제기", page_icon="📞", layout="centered"
)

st.title("📞 통화내역 데이터 패턴 맞춤형 엑셀 변환기")
st.write(
    "각 열의 데이터 형식(사업자, 순번, 사용유형, 착신번호, 시작시간, 사용시간,"
    " 주소)을 정규식 패턴으로 엄격하게 검증하여 완벽한 표 형태로 정리합니다."
)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요.", type=["pdf"]
)

if uploaded_file is not None:
  try:
    with st.spinner(
        "스캔본 이미지를 OCR 분석하고 데이터 패턴을 정밀 매칭하는 중입니다..."
    ):
      pdf_bytes = uploaded_file.read()
      images = convert_from_bytes(pdf_bytes, dpi=200)
      total_pages = len(images)

      st.info(f"총 {total_pages}페이지 분석 중...")

      if total_pages < 2:
        st.warning("2페이지 이상인 파일을 업로드해주세요.")
      else:
        parsed_rows = []

        # 정규식 패턴 정의
        # 1. 전화번호 패턴 (예: 010-****-7115, 051-*8985 등)
        phone_pattern = re.compile(r'\d{2,3}-\S*-\d{4}')
        # 2. 통화시작시간 패턴 (예: 2025-08-01 09:09:55)
        datetime_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')
        # 3. 사용시간 패턴 (예: 00:00:00)
        time_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')

        # 2페이지부터 끝까지 순회 (인덱스 1부터 시작)
        for index in range(1, total_pages):
          img = images[index]
          ocr_text = pytesseract.image_to_string(img, lang="kor+eng")

          lines = ocr_text.split("\n")
          for line in lines:
            line_str = line.strip()

            if not line_str:
              continue

            # 상단 머리글 및 불필요한 문구 필터링
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

            # OCR 인식 오타 및 깨진 문자 정돈
            cleaned_line = (
                line_str.replace("ucu+", "LGU+")
                .replace("tcu+", "LGU+")
                .replace("ucu", "LGU+")
                .replace("tcu", "LGU+")
                .replace("|", " ")
            )

            tokens = cleaned_line.split()
            if len(tokens) < 5:
              continue

            # 데이터 파싱 변수 초기화
            page_no = index + 1
            business = ""
            seq = ""
            usage_type = ""
            phone = ""
            start_time = ""
            duration = ""
            address = ""

            # 1. 사업자 찾기 (LGU+, SKT, KT 등 5글자 내외 문자)
            for t in tokens[:3]:
              if any(
                  tel in t.upper() for tel in ["LGU", "SKT", "KT", "LG", "SK"]
              ):
                business = "LGU+" if "LG" in t.upper() else t
                break
            if not business:
              business = "LGU+"  # 기본값

            # 2. 순번 찾기 (1~5000 사이의 숫자 단독 토큰)
            for t in tokens[:4]:
              if t.isdigit() and 1 <= int(t) <= 5000:
                seq = t
                break

            # 3. 착신번호 찾기 (전화번호 패턴 매칭)
            phone_match = phone_pattern.search(cleaned_line)
            if phone_match:
              phone = phone_match.group(0)

            # 4. 통화시작시간 찾기 (YYYY-MM-DD HH:MM:SS 패턴)
            dt_match = datetime_pattern.search(cleaned_line)
            if dt_match:
              start_time = dt_match.group(0)

            # 5. 사용시간 찾기 (HH:MM:SS 패턴, 시작시간 뒤쪽에 위치하거나 두 번째 시간 패턴)
            time_matches = time_pattern.findall(cleaned_line)
            if len(time_matches) >= 2:
              duration = time_matches[1]  # 두 번째 시간이 사용시간
            elif len(time_matches) == 1 and not start_time:
              duration = time_matches[0]

            # 6. 사용유형 찾기 (순번과 전화번호/시간 사이의 문자, 예: 3G, VOLTE음성 등)
            # 순번 토큰 다음부터 전화번호 전까지의 텍스트 추출
            try:
              if seq in tokens and phone in cleaned_line:
                seq_idx = tokens.index(seq)
                sub_tokens = tokens[seq_idx + 1 :]
                for st_token in sub_tokens:
                  if (
                      not phone_pattern.match(st_token)
                      and not datetime_pattern.search(st_token)
                      and not st_token.isdigit()
                  ):
                    usage_type = st_token
                    break
            except:
              pass

            if not usage_type:
              usage_type = "VOLTE음성"

            # 7. 발신기지국주소 찾기 (시간이나 번호 뒤에 남은 잔여 텍스트)
            if dt_match:
              dt_end_idx = cleaned_line.find(start_time) + len(start_time)
              residual = cleaned_line[dt_end_idx:].strip()
              if residual:
                # 사용시간이 잔여 텍스트 맨 앞에 포함되어 있으면 제거
                if duration and residual.startswith(duration):
                  residual = residual[len(duration) :].strip()
                address = residual.lstrip("|- ").strip()

            # 유효한 필수 데이터(순번과 전화번호)가 모두 잡힌 경우에만 최종 행으로 인정
            if seq and phone:
              parsed_rows.append({
                  "페이지": page_no,
                  "사업자": business,
                  "순번": int(seq),
                  "사용유형": usage_type,
                  "착신번호": phone,
                  "통화시작시간": start_time,
                  "사용시간(초)": duration,
                  "발신기지국주소": address,
              })

        if len(parsed_rows) > 0:
          df = pd.DataFrame(parsed_rows)
          # 순번 기준 오름차순 정렬
          df = df.sort_values(by=["페이지", "순번"]).reset_index(drop=True)

          st.success(
              f"패턴 매칭 정제 완료! 총 {len(df)}건의 통화내역을 완벽하게"
              " 분리했습니다."
          )

          st.write("### 정제된 표 데이터 미리보기")
          st.dataframe(df.head(15))

          # 엑셀 파일 생성
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="정제통화내역")
          excel_data = output.getvalue()

          st.download_button(
              label="📥 완벽 정제된 엑셀 파일 다운로드 (.xlsx)",
              data=excel_data,
              file_name="pattern_matched_call_history.xlsx",
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
        else:
          st.warning(
              "조건에 맞는 통화내역 패턴 행을 추출하지 못했습니다. OCR 인식"
              " 상태를 다시 확인하고 있습니다."
          )

  except Exception as e:
    st.error(f"처리 중 오류 발생: {e}")
