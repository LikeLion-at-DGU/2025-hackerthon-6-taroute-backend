import requests
from django.conf import settings

BASE = "https://api.openai.com/v1/chat/completions"

# 키워드 추출용 슬롯
SLOT_SCHEMA = {
        "type": "object",
        "properties": {
            "radius": {"type":["string", "null"]},
            "budget": {"type":["string", "null"]},
            "vibe": {"type":["string", "null"]},
            "category": {"type":["string", "null"]},
            "time": {"type":["string", "null"]}
        },
        "required": ["radius", "budget", "vibe", "category", "time"],
        "additionalProperties": False
    }

# 질문당 4개의 객관식 보기 옵션
QUESTION_TEXT_ITEM = {
    "type": "object",
    "properties": {
        "que_id" : {"type" : "integer"},
        "question": {"type": "string"},
        "options": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {"type": "string"}
        }
    },
    "required": ["que_id","question", "options"],
    "additionalProperties": False
}
# 질문+옵션 4개 연결
QUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": QUESTION_TEXT_ITEM
        }
    },
    "required": ["questions"],
    "additionalProperties": False
}

def _headers():
    return {
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

# create_question을 호출하면 챗봇에게 질문과 객관식 4개 리스트들을 뽑아달라고 해서 저장
def create_question(input_text: str = "지금 질문 리스트 5개를 뽑아줘", lang: str = "ko", model: str = "gpt-4o-mini"):
    system_prompt = (
            "너는 사용자의 무의식에 숨겨진 취향과 희망을 읽어내어, 가장 완벽한 장소를 점지해주는 신비롭고 현명한 '타로마스터 타루'입니다. "
            "다음 5가지 핵심 슬롯(radius, budget, vibe, category, time)의 정보를 정확히 하나씩 파악하기 위한 객관식 질문을 순서대로 제시합니다. "
            "\n\n**중요한 규칙**: "
            "\n1. 각 질문은 반드시 하나의 슬롯만을 타겟팅해야 합니다"
            "\n2. 선택지에는 실제 장소 검색에 활용할 수 있는 구체적인 키워드가 포함되어야 합니다"
            "\n3. 질문은 타로틱하고 신비롭게 하되, 선택지는 명확하게 구성하세요"
            "\n\n**각 슬롯별 가이드라인**: "
            "\n\n**첫 번째 질문 (radius 슬롯)**: 이동 거리에 대한 질문"
            "\n- 선택지 형태: 거리감을 자연스럽게 표현하되 핵심 거리 정보 포함"
            "\n- 예시: '가까운 숨결 속 30분 거리', '운명이 이끄는 1시간 거리', '별빛 따라 2시간 거리', '신비한 여정 3시간 거리'"
            "\n- 변형 가능: '짧은 여정 30분', '적당한 거리 1시간', '멀리 떨어진 2시간', '먼 곳까지 3시간'"
            "\n\n**두 번째 질문 (budget 슬롯)**: 예산/가격대에 대한 질문"
            "\n- 선택지 형태: 가격대를 자연스럽게 표현하되 핵심 가격 정보 포함"
            "\n- 예시: '소박한 마음으로 저렴한', '균형 잡힌 에너지로 적당한', '품격 있는 선택으로 고급스런', '운명처럼 특별한 럭셔리'"
            "\n- 변형 가능: '가볍게 즐길 수 있는 저렴한', '적당한 투자로 적당한', '특별한 경험을 위한 고급스런', '최고급 서비스를 위한 럭셔리'"
            "\n\n **세 번째 질문 (vibe 슬롯)**: 분위기에 대한 질문"
            "\n- 선택지 형태: 분위기를 자연스럽게 표현하되 핵심 분위기 정보 포함"
            "\n- 예시: '고요한 조용한', '가득한 활기찬', '속삭임 같은 로맨틱한', '도시의 세련된'"
            "\n- 변형 가능: '차분한 마음을 위한 조용한', '에너지 넘치는 활기찬', '사랑의 기운이 있는 로맨틱한', '모던한 감각의 세련된'"
            "\n\n **네 번째 질문 (category 슬롯)**: 장소 유형에 대한 질문"
            "\n- 선택지 형태: 장소 유형을 자연스럽게 표현하되 핵심 장소 정보 포함"
            "\n- 예시: '향기로운 여유가 흐르는 카페', '영혼을 채우는 특별한 맛집', '지혜가 깃든 신비로운 문화공간', '모험이 기다리는 관광명소'"
            "\n- 변형 가능: '디저트가 맛있는 집', '배를 든든히 할 수 있는 공간', '예술의 향기를 느낄 수 있는 장소', '특색있는 경험을 할 수 있는 공간'"
            "\n- 추가 변형: '커피 향이 가득한 장소소', '특별한 요리를 맛볼 수 있는 장소', '역사와 문화를 느낄 수 있는 공간', '자연이나 문화를 만끽할 수 있는 장소'"
            "\n\n**다섯 번째 질문 (time 슬롯)**: 시간대에 대한 질문"
            "\n- 선택지 형태: 시간대를 자연스럽게 표현하되 핵심 시간 정보 포함"
            "\n- 예시: '새로운 시작의 기운 가득한 아침', '에너지 넘치는 점심', '노을빛 추억을 만드는 저녁', '별이 수놓은 신비로운 밤'"
            "\n- 변형 가능: '상쾌한 기운의 아침', '따뜻한 햇살의 점심', '차분한 마음의 저녁', '고요한 평화의 밤'"
            "\n- 추가 변형: '새롭게 시작하는 아침', '활기찬 에너지의 점심', '편안한 휴식의 저녁', '신비로운 분위기의 밤'"
            "\n\n**최종 요구사항**: "
            "\n- 질문은 신비롭고 타로틱하게 표현하되 50자 이내"
            "\n- 선택지는 자연스러운 문장으로 구성하되 핵심 정보는 명확히 전달"
            "\n- 핵심 정보(거리, 가격, 분위기, 장소유형, 시간대)는 반드시 포함하되 다양한 표현 사용"
            "\n- 예시: '카페' → '디저트가 맛있는', '커피 향이 가득한' 등으로 변형 가능"
            "\n- 선택지도 타로 분위기를 살린 시적이고 감성적인 표현 사용"
            "\n- '지갑','예산','자금','관광명소'와 같은 직설적인 단어는 사용하지 말 것."
            "\n- 부드러운 반말 사용"
            "\n- 가장 중요한건, 질문과 대답이 항시 새로워야함. 직전에 썼던 표현들은 지향할 것. 부드러운 반말 사용"
            "\n- 또한 예시를 참고해서 표현하는거지, 예시와 똑같은 표현 쓰지 말 것. 변형을 보고 응용 해야되는거지, 따라하면 안됨."
            "\n- que_id는 1부터 5까지 순서대로"
        )
    
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "quest_schema",
                "schema": QUEST_SCHEMA,
                "strict": True
            }
        }
    }

    r = requests.post(BASE, headers=_headers(), json=body, timeout=(5, 20))
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e

    return r.json()

#create_chat을 호출하면 그 저장한 질문을 하나씩 뽑아서 프론트에 띄우고, 답변에 대해서는 기존처럼 slot의 값을 추출하여 저장
def create_chat(input_text: str, lang: str = "ko", model: str = "gpt-4o-mini"):

    if lang.lower() == "ko":
        system_prompt = (
            "너는 한국어로만 대답하는 유용한 타로마스터야."
            "사용자의 무의식에서 취향과 희망사항을 알아내어 사용자가 원하는 장소의 키워드를 추출해. "
            "아래 슬롯을 가능한 만큼 채워서 JSON으로 반환해."
            "모르는 값은 다른 슬롯의 값을 참고해서 적절한 내용으로 채워, 슬롯의 값이 null이 되면 안돼"
        )
    else:
        system_prompt = (
            "You are a helpful tarot master that only responds in English. "
            "Infer user's tastes and wishes and return keywords as JSON by filling the slots."
        )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "slots_schema",
                "schema": SLOT_SCHEMA,
                "strict": True
            }
        }
    }

    r = requests.post(BASE, headers=_headers(), json=body, timeout=(5, 20))
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e

    return r.json()

# 리뷰 기반 정확한 정보 요약 (20자 이내)
def create_accurate_summary(place_name: str, reviews: list, lang: str = "ko", model: str = "gpt-4o-mini"):
    """구글 리뷰를 기반으로 정확한 정보의 한줄 요약 생성 (20자 이내)"""
    
    if not reviews:
        return None
    
    # 리뷰 텍스트 합치기 (최대 5개)
    review_texts = reviews[:5]
    combined_reviews = "\n".join([f"- {review}" for review in review_texts])
    
    if lang.lower() == "ko":
        system_prompt = (
            "당신은 장소 정보 전문가입니다. "
            "구글 리뷰들을 바탕으로 이 장소의 핵심 특징을 30자 이내로 정확하고 간결하게 요약해주세요. "
            "요약 시 반드시 다음 우선순위를 따라주세요: 1) 주요 메뉴/음식 종류, 2) 맛/품질, 3) 서비스/분위기, 4) 가격대 "
            "리뷰에서 언급된 구체적인 메뉴명이나 음식 종류를 반드시 포함해주세요. "
        )
        user_prompt = f"장소명: {place_name}\n\n리뷰들:\n{combined_reviews}\n\n이 장소를 30자 이내로 요약하되, 반드시 주요 메뉴나 음식 종류를 포함해서 실용적인 한줄 요약을 작성해주세요."
    else:
        system_prompt = (
            "You are a place information expert. "
            "Summarize this place's key features accurately within 30 characters based on Google reviews. "
            "Follow this priority: 1) Main menu/food type, 2) Taste/quality, 3) Service/atmosphere, 4) Price range "
            "Always include specific menu items or food types mentioned in reviews. "
            "Examples: 'Spicy hotpot & noodles restaurant', 'Coffee & dessert specialty cafe', 'BBQ & soup Korean restaurant'"
        )
        user_prompt = f"Place: {place_name}\n\nReviews:\n{combined_reviews}\n\nSummarize this place within 30 characters, making sure to include main menu or food types for practical information."
    
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 100,
        "temperature": 0.3  # 정확하고 일관성 있는 요약을 위해 낮은 temperature 사용
    }
    
    r = requests.post(BASE, headers=_headers(), json=body, timeout=(5, 20))
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e
    
    response_data = r.json()
    
    # 응답에서 내용 추출
    try:
        summary = response_data["choices"][0]["message"]["content"].strip()
        
        # 따옴표 제거 및 길이 제한
        summary = summary.replace('"', '').replace("'", '')
        
        # 한국어의 경우 30자, 영어의 경우 40자 제한
        max_length = 30 if lang.lower() == "ko" else 40
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
        
    except (KeyError, IndexError) as e:
        raise ValueError(f"OpenAI 응답 파싱 실패: {e}")