# from datetime import timezone
# from venv import logger
# from typing import List, Dict, Optional, Tuple

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


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
#             model="gpt-5-mini",  # 최신 모델 사용
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
#             "model": "gpt-5-mini",
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
CONTENT = "https://api.openai.com/v1/moderations"

def _headers():
    return {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

# 리뷰를 데이터로 AI 요약
def openai_summary(input_text:str, lang: str = "ko", model: str = "gpt-5-mini"):
    # 언어별 시스템 프롬프트 설정
    if lang == "en":
        system_prompt = (
            "You are a place information expert. "
            "Based on the reviews and place information provided by users, "
            "please create a summary that helps understand this place at a glance. "

            "Summary writing rules are as follows:\n"
            "1. Write within 100 characters, in one paragraph\n"
            "2. Emphasize the characteristics, atmosphere, and main attraction points of the place\n"
            "3. Include useful information (price, location, convenience, etc.) that visitors should know, if available\n"
            "4. Maintain a polite and friendly tone\n"
            "5. Avoid exaggerated or subjective promotional expressions, and write from an objective and balanced perspective"
        )
    else:  # 한국어 (기본값)
        system_prompt = (
            "당신은 장소 정보 전문가입니다. "
            "사용자가 제공한 리뷰와 장소 정보를 바탕으로 "
            "이 장소를 한눈에 이해할 수 있는 요약문을 작성하세요. "

            "요약 작성 규칙은 다음과 같습니다:\n"
            "1. 반드시 글자 수는 100자가 넘지 않게, 한 문단으로 작성\n"
            "2. 장소의 특징, 분위기, 주요 매력 포인트를 강조\n"
            "3. 방문자가 알아야 할 유용한 정보(가격·위치·편의 등)가 있다면 최소한으로 포함\n"
            "4. 정중하고 친근한 톤을 유지\n"
            "5. 과장되거나 주관적인 광고성 표현은 피하고, 객관적이고 균형 잡힌 시각으로 작성"
            "6. 글자 수를 세어보고 100자를 초과하면 더 짧게 다시 작성하세요"
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


def create_crawled_reviews_summary(place_name, google_reviews=None, blog_reviews=None, lang="ko", model="gpt-4o-mini"):
    """크롤링된 리뷰들을 기반으로 AI 요약을 생성하는 함수
    
    Args:
        place_name (str): 장소명
        google_reviews (list): 구글맵 리뷰 리스트
        blog_reviews (list): 블로그 리뷰 리스트
        lang (str): 언어 (기본 한국어)
        model (str): 사용할 AI 모델
    
    Returns:
        str: "[가게명]은 ~~[크롤링된 ai 요약]~~" 형태의 요약문
    """
    try:
        # 입력 데이터 유효성 검사
        if not place_name:
            raise ValueError("place_name은 필수입니다.")
        
        google_reviews = google_reviews or []
        blog_reviews = blog_reviews or []
        
        if not google_reviews and not blog_reviews:
            logger.warning(f"크롤링된 리뷰가 없어 요약 생성 불가 (장소: {place_name})")
            return None  # 실제 리뷰가 없으면 요약 생성하지 않음
        
        # 구글맵 리뷰만 사용 (블로그 리뷰는 제외)
        all_reviews = []
        
        if google_reviews:
            all_reviews.append("=== 구글맵 리뷰 ===")
            all_reviews.extend(google_reviews[:8])  # 최대 8개
        
        input_text = "\n\n".join(all_reviews)
        
        # 길이 제한 (너무 길면 잘라내기)
        if len(input_text) > 4000:
            input_text = input_text[:4000] + "..."
        
        # 언어별 시스템 프롬프트 설정
        if lang == "en":
            system_prompt = (
                f"You are a Google Maps review analysis expert. "
                f"Please analyze actual visitor reviews for '{place_name}' collected from Google Maps "
                f"and create a summary that captures the characteristics of this place at a glance.\n\n"
                
                f"Summary writing rules:\n"
                f"1. Must start with '{place_name} is'\n"
                f"2. Write within 100 characters, but don't miss key information\n"
                f"3. Prioritize the following elements:\n"
                f"   - Food/service taste and quality\n"
                f"   - Atmosphere and interior\n"
                f"   - Price range and value for money\n"
                f"   - Service and friendliness\n"
                f"   - Special menus or advantages\n"
                f"4. Write in an objective and balanced tone\n"
                f"5. Focus on actual visitors' vivid experiences rather than exaggerated expressions\n"
                f"6. If there are negative opinions, mention them in a balanced way"
            )
            user_content = f"Place name: {place_name}\n\nActual visitor reviews collected from Google Maps:\n{input_text}"
        else:  # 한국어 (기본값)
            system_prompt = (
                f"당신은 구글맵 리뷰 분석 전문가입니다. "
                f"구글맵에서 수집된 '{place_name}'에 대한 실제 방문객 리뷰들을 분석하여 "
                f"이 장소의 특징을 한눈에 파악할 수 있는 요약문을 작성하세요.\n\n"
                
                f"요약 작성 규칙:\n"
                f"1. 반드시 '{place_name}은' 또는 '{place_name}는'으로 시작하세요\n"
                f"2. 100자 이내로 간결하게 작성하되, 핵심 정보는 빠뜨리지 마세요\n"
                f"3. 다음 요소들을 우선적으로 포함:\n"
                f"   - 음식/서비스의 맛과 품질\n"
                f"   - 분위기와 인테리어\n"
                f"   - 가격대와 가성비\n"
                f"   - 서비스와 친절도\n"
                f"   - 특별한 메뉴나 장점\n"
                f"4. 객관적이고 균형 잡힌 톤으로 작성\n"
                f"5. 과장된 표현보다는 실제 방문자들의 생생한 경험을 중심으로 서술\n"
                f"6. 만약 부정적인 의견도 있다면 균형있게 언급"
                f"7. 글자 수를 세어보고 100자를 초과하면 더 짧게 다시 작성하세요"
            )
            user_content = f"장소명: {place_name}\n\n구글맵에서 수집된 실제 방문객 리뷰들:\n{input_text}"
        
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_completion_tokens": 1000
        }
        
        print(f"🚀 [DEBUG] OpenAI API 요청 시작 - 모델: {model}, 장소: {place_name}")
        print(f"🚀 [DEBUG] 요청 데이터: {body}")
        
        try:
            r = requests.post(BASE, headers=_headers(), json=body, timeout=(10, 120))
            print(f"🚀 [DEBUG] HTTP 응답 코드: {r.status_code}")
            r.raise_for_status()
            
            data = r.json()
            print(f"🚀 [DEBUG] OpenAI API 응답 성공!")
            print(f"🚀 [DEBUG] 전체 응답: {data}")
            
            ai_summary = ((data.get("choices") or [])[0].get("message") or {}).get("content", "").strip()
            print(f"🚀 [DEBUG] 추출된 AI 요약: '{ai_summary}'")
            
        except requests.HTTPError as http_err:
            print(f"❌ [DEBUG] HTTP 에러: {http_err}")
            print(f"❌ [DEBUG] 응답 내용: {http_err.response.text if http_err.response else 'No response'}")
            raise
        except Exception as e:
            print(f"❌ [DEBUG] 기타 에러: {e}")
            raise
        
        # 응답이 없거나 빈 경우 None 반환
        if not ai_summary:
            logger.warning(f"AI 요약 생성 결과가 비어있음 (장소: {place_name})")
            return None
        
        # 장소명으로 시작하지 않는 경우 보정
        if not (ai_summary.startswith(f"{place_name}은") or ai_summary.startswith(f"{place_name}는")):
            ai_summary = f"{place_name}은 {ai_summary}"
        
        return ai_summary
        
    except requests.HTTPError as e:
        error_detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI API 호출 실패: {e.response.status_code} - {error_detail}") from e
    except Exception as e:
        raise Exception(f"크롤링 리뷰 요약 생성 중 오류: {str(e)}") from e

############################################################################################################################
# 위키 리뷰 내용 => 유해 여부 판정
def content_moderation(input_text:str, lang: str = "ko", model: str = "omni-moderation-latest"):
    # 언어별 시스템 프롬프트 설정
    if lang == "en":
        system_prompt = (
            "You are a profanity sanitizer for English user reviews."
            "Keep the original meaning and tone, but replace only profanities with ** or neutral wording." 
            "Do not add or remove information. Output English only"
        )
    else:  # 한국어 (기본값)
        system_prompt = (
            "한국 사용자 리뷰의 욕설을 걸러내는 도구입니다."
            "원래의 의미와 어조는 유지하되, 욕설만 ** 또는 중립적인 표현으로 바꿔주세요."
            "정보를 추가하거나 삭제하지 마세요. 한국어만 출력하세요."

            "요구사항:"
            "- 비속어/욕설/모멸적 표현만 `**`로 마스킹하거나 완곡어로 대체"
            "- 문장 구조와 정보는 유지"
            "- 링크/이메일/전화번호는 그대로 둠"
            "- 결과만 출력"
        )
    
    body = {
        "model": model,
        "input": system_prompt
    }

    r = requests.post(CONTENT, headers=_headers(), json=body, timeout=(5,20))
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e

    data = r.json()
    flag = ((data.get("results") or [])[0].get("flagged") or {})

    moderate = []
    moderate.append({
        "data": data,
        "flag": flag
    })
    return moderate