import networkx as nx
from core.distance import calculate_distance
from .kakao import look_category


def filter(day, data):
  result = []

  for place_id, place_info in data.items():
    times = place_info.get("running_time", [])
    name = place_info.get('place_name')
    location = place_info.get('location')

    # 해당 요일 라인만 추출
    filter_data = [line for line in times if line.startswith(day)]

    # 휴무일 체크
    is_closed = any("휴무" in line for line in filter_data)

    # 카카오 카테고리 검색
    data_type = look_category(name, location.get("x"), location.get("y"), radius=2000)

    if filter_data and not is_closed: #해당 요일에 영업 중인 장소의 데이터 반환
      result.append({
          "place_name": name,
          "times": filter_data,
          "location":location,
          "type": data_type
      })
  
  return result

def find_nearest_place(places, mylat, mylng):
    min_distance = 0
    nearest_idx = 0
    
    for i, place in enumerate(places):
        lat = float(place["location"]["latitude"])
        lng = float(place["location"]["longitude"])
        distance = calculate_distance(mylat, mylng, lat, lng)
        
        if distance < min_distance:
            min_distance = distance
            nearest_idx = i
            
    return nearest_idx

def build_distance_matrix(places, mylat=None, mylng=None):
    # 2차원 km 리스트로 반환
    n = len(places)
    G = nx.complete_graph(n)
    # M = [[0]*n for _ in range(n)]

    # 노드 데이터
    for i, p in enumerate(places):
        G.nodes[i]["latitude"] = p["location"]["latitude"]
        G.nodes[i]["longitude"] = p["location"]["longitude"]

    for i in range(n):
        for j in range(i+1, n):
            d = calculate_distance(G.nodes[i]["latitude"], G.nodes[i]["longitude"],
                                   G.nodes[j]["latitude"], G.nodes[j]["longitude"])
            G[i][j]["weight"] = d
            G[j][i]["weight"] = d

    # 사용자 위치에서 가장 가까운 장소를 startidx로 함
    start_idx = None
    if mylat is not None and mylng is not None:
        start_idx = find_nearest_place(places, mylat, mylng)

    return G, start_idx

# 카테고리 제약 조건 확인
def check_type(places, path):
    # 전체 장소 카테고리 수 확인
    categories = [places[i].get("type") for i in path]
    category_set = set(categories)

    print(f"경로 카테고리: {categories}")
    print(f"카테고리 종류: {category_set}")
    
    # 만약 FD6와 CE7만 있다면 제약조건 무시 (예외 처리)
    if category_set <= {"FD6", "CE7"}:
        print("FD6와 CE7만 있어 제약조건 무시함")
        return True
        
    for i in range(len(path)-1):
        a, b = places[i], places[i+1]
        a_type = a.get("type")
        b_type = b.get("type")
        print(f"검사: {i}번째({a_type}) → {i+1}번째({b_type})")

        # 관광 <-> 문화 연속 제한, 다른 선택지가 없으면 허용
        if (a.get("type") == "AT4" and b.get("type") == "CT1") or \
            (a.get("type") == "CT1" and b.get("type") == "AT4"):
            print(f"  ❌ 관광↔문화 연속 배치됨")
            # 경로의 길이가 짧으면(선택지가 적으면) 허용
            if len(path) <= 4:
                print("  ✅ 경로가 짧아 제약 무시")
                continue
            print("  ❌ 경로 제약 위반: 관광↔문화 규칙")
            return False
        
        # 식당 -> 카페가 이어서 오도록
        if a.get("type") == "FD6" and b.get("type") != "CE7":
            print(f"  ❌ 식당({a_type}) 다음 카페({b_type})가 아님")
            # 타입에 카페가 없으면 무시
            if "CE7" not in category_set:
                print("  ✅ 카페가 없어서 제약 무시")
                continue
            # 카페가 있지만 경로상 배치 불가능한 경우도 허용
            if categories.count("CE7") < categories.count("FD6"):
                print("  ✅ 카페 수가 식당보다 적어 제약 무시")
                continue
            print("  ❌ 경로 제약 위반: 식당→카페 규칙")
            return False

    print("✅ 모든 제약 조건 통과!")
    return True

def tsp_route(places, cycle=False, mylat=None, mylng=None, start_idx=None, end_idx=None):
    # 근사 TSP 경로 구하기, cycle=False 일반 경로(시작!=끝), weight 가중치 default
    if not places:
        return []

    G, nearest_idx = build_distance_matrix(places, mylat, mylng)
    # 사용자와 가까운 장소를 start_idx
    if start_idx is None and nearest_idx is not None:
        start_idx = nearest_idx

    for i in range(10): # 여러번 반복해서 조건 만족하는 값 찾기
        path = nx.approximation.traveling_salesman_problem(G, cycle=cycle, weight="weight")
        print(f"\n===== 시도 {i+1} =====")

        # path는 노드 인덱스 리스트. cycle=True면 마지막이 첫 노드로 돌아오는 형식일 수 있음.
        def rotate_to_start(seq, start):
            if start is None:
                return seq
            k = seq.index(start)
            return seq[k:] + seq[:k]
        
        if start_idx is not None:
            path = rotate_to_start(path, start_idx)
            print(f"시작점 {start_idx}로 경로 조정")

        print(f"경로: {path}")
        if check_type(places, path):
                print("✅ 유효한 경로 찾음!")
                return path
        else:
            print("❌ 제약조건 불만족, 다시 시도")
        
    print("\n⚠️ 10번 시도했지만 조건 만족 경로 못 찾음, 제약 없이 반환")
    # 조건에 만족하지 않으면 제약 없이 반환
    path = nx.approximation.traveling_salesman_problem(G, cycle=cycle, weight="weight") 

    if start_idx is not None:
        path = rotate_to_start(path, start_idx)

    return path

def route_info(places, path):
    # 동선 정보 가공
    data = []
    for i in path:
        p = places[i]
        data.append({
            "place_name": p.get("place_name"),
            "running_time": p.get("times"),
            "latitude": p["location"]["latitude"],
            "longitude": p["location"]["longitude"]
        })
    return data

# breaktime 피해서 짜야함 (옵션)