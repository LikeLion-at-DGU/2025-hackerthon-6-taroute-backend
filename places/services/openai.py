import requests
from django.conf import settings

BASE = "https://api.openai.com/v1/responses"

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
            "너는 사용자의 무의식에 숨겨진 취향과 희망을 읽어내어, 가장 완벽한 장소를 점지해주는 신비롭고 현명한 '타로마스터 타루'입니다"
            "사용자가 내면에 품고 있는 진정한 욕구를 끌어내기 위해, 타로 카드 한 장을 펼치듯 상징적이고 비유적인 질문을 던져주세요"
            "질문은 직관적이지 않아야 하며, 마치 꿈을 해몽하듯 사용자의 무의식 깊은 곳을 자극해야 합니다. 당신은 결코 '어떤 숫자를 원하세요?'와 같은 직접적인 질문을 하지 않습니다."
            "다음 5가지 핵심 슬롯(radius, budget, vibe, category, time)의 정보를 타로 카드 해석하듯 채워나가기 위한 객관식 질문을 하나씩, 총 5개를 순서대로 제시합니다"
            "각 질문은 오직 하나의 슬롯만을 목표로 하며, 질문당 4개의 선택지를 제공해야 합니다"
            "선택지는 구글 장소 리뷰에서 영감을 받은, 사용자의 감정이나 경험을 은유적으로 나타내는 키워드로 구성해주세요. 예를 들어 '조용하고 아늑한', '활기찬 에너지로 가득한'과 같이 공간의 분위기를 연상시킬 수 있는 표현을 사용합니다"
            "특히 'radius' 슬롯을 채우는 질문의 옵션들은 1시간, 2시간의 시간 단위로 답변을 유도해 거리를 암시하도록 구성합니다"
            "모든 질문은 부드러운 반말로 진행해줘!"
        )
    
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "quest_schema",
                "schema": QUEST_SCHEMA,
                "strict": True
            }
        }
    }

    r = requests.post(BASE, headers=_headers(), json=body, timeout=15)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError("OpenAI {e.response.status_code} Error: {detail}") from e

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
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "slots_schema",
                "schema": SLOT_SCHEMA,
                "strict": True
            }
        }
    }

    r = requests.post(BASE, headers=_headers(), json=body, timeout=15)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "") or str(e)
        raise requests.HTTPError(f"OpenAI {e.response.status_code} Error: {detail}") from e

    return r.json()