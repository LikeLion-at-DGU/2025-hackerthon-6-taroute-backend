# from datetime import timezone
# from venv import logger
# from typing import List, Dict, Optional, Tuple

import requests
from django.conf import settings


# def generate_ai_summary(place_name: str, reviews: List[str] = None, basic_info: str = None) -> Tuple[str, Dict]:
#     """OpenAI API를 사용하여 장소에 대한 AI 요약 생성
    
#     Args:
#         place_name: 장소명
#         reviews: 리뷰 텍스트 리스트 (선택사항)
#         basic_info: 기본 정보 텍스트 (선택사항)
    
#     Returns:
#         Tuple[요약 텍스트, 메타데이터]
#     """
#     if not settings.OPENAI_API_KEY:
#         raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
#     try:
#         from openai import OpenAI
#     except ImportError:
#         raise RuntimeError("openai 패키지가 설치되어야 합니다: pip install openai")
    
#     client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
#     # 프롬프트 구성
#     prompt_parts = [
#         f"'{place_name}'에 대한 종합적인 요약을 작성해주세요.",
#         "다음 정보들을 바탕으로 이 장소의 특징, 분위기, 추천 포인트를 300자 이내로 요약해주세요.",
#     ]
    
#     # 기본 정보가 있는 경우 추가
#     if basic_info:
#         prompt_parts.append(f"\n기본 정보: {basic_info}")
    
#     # 리뷰가 있는 경우 추가 (최대 5개까지만)
#     if reviews:
#         review_text = "\n".join(reviews[:5])
#         prompt_parts.append(f"\n사용자 리뷰들:\n{review_text}")
    
#     # 지침 추가
#     prompt_parts.extend([
#         "\n요약 시 다음 사항을 고려해주세요:",
#         "- 객관적이고 균형잡힌 시각으로 작성",
#         "- 핵심적인 특징과 매력 포인트 강조", 
#         "- 방문자들이 알아야 할 주요 정보 포함",
#         "- 정중하고 친근한 톤으로 작성"
#     ])
    
#     prompt = "\n".join(prompt_parts)
    
#     try:
#         # OpenAI API 호출
#         response = client.chat.completions.create(
#             model="gpt-5",  # 최신 모델 사용
#             messages=[
#                 {
#                     "role": "system", 
#                     "content": "당신은 장소 정보 전문가입니다. 주어진 정보를 바탕으로 정확하고 유용한 장소 요약을 작성합니다."
#                 },
#                 {"role": "user", "content": prompt}
#             ],
#             max_completion_tokens=500,       # 토큰 제한
#             # temperature=0.7,      # 창의성과 일관성의 균형
#         )
        
#         ai_summary = response.choices[0].message.content.strip()
        
#         # 메타데이터 생성
#         metadata = {
#             "model": "gpt-5",
#             "prompt_tokens": response.usage.prompt_tokens,
#             "completion_tokens": response.usage.completion_tokens,
#             "total_tokens": response.usage.total_tokens,
#             "generated_at": timezone.now().isoformat(),
#             "review_count": len(reviews) if reviews else 0,
#             "has_basic_info": bool(basic_info),
#         }
        
#         logger.info(f"AI 요약 생성 성공: {place_name}, 토큰 사용량: {response.usage.total_tokens}")
#         return ai_summary, metadata
        
#     except Exception as e:
#         logger.error(f"OpenAI API 호출 실패: {e}")
#         raise
    

BASE = "https://api.openai.com/v1/chat/completions"

def _headers():
    return {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

# 리뷰를 데이터로 AI 요약
def openai_summary(input_text:str, lang: str = "ko", model: str = "gpt-4o-mini"):
    system_prompt = (
            "당신은 장소 정보 전문가입니다. "
            "사용자가 제공한 리뷰와 장소 정보를 바탕으로 "
            "이 장소를 한눈에 이해할 수 있는 요약문을 작성하세요. "

            "요약 작성 규칙은 다음과 같습니다:\n"
            "1. 글자 수는 200자 이내, 한 문단으로 작성\n"
            "2. 장소의 특징, 분위기, 주요 매력 포인트를 강조\n"
            "3. 방문자가 알아야 할 유용한 정보(가격·위치·편의 등)가 있다면 간단히 포함\n"
            "4. 정중하고 친근한 톤을 유지\n"
            "5. 과장되거나 주관적인 광고성 표현은 피하고, 객관적이고 균형 잡힌 시각으로 작성"
        )
    
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
    }

    r = requests.post(BASE, headers=_headers(), json=body, timeout=(5,100))
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e

    data = r.json()
    ai_summary = ((data.get("choices") or [])[0].get("message") or {}).get("content")
    return ai_summary