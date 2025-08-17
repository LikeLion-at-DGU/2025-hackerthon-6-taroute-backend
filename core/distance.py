def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간의 거리 계산 (하버사인 공식)
    
    Args:
        lat1, lon1: 첫 번째 지점의 위도, 경도
        lat2, lon2: 두 번째 지점의 위도, 경도
    
    Returns:
        거리(km)
    """
    import math
    
    # 지구 반지름 (km)
    R = 6371.0
    
    # 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도, 경도 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # 하버사인 공식 적용
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # 거리 계산
    distance = R * c
    return round(distance, 2)