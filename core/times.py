# 영업시간 정보 데이터 가공
DAYS = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]

def format_time(h, m):
    return f"{h:02d}:{m:02d}"

def format_running(running_time):
    result = []
    all_breaks = []  # 모든 요일의 브레이크 타임을 저장할 리스트
    
    for d in range(7):
        day_periods = []
        try:
            # 예외처리: open과 close가 모두 있는 경우만 추가
            day_periods = [
                p for p in running_time.get("periods", []) 
                if p.get("open") and p.get("close") and 
                p["open"].get("day") == d and 
                p["open"].get("hour") is not None and 
                p["open"].get("minute") is not None and
                p["close"].get("hour") is not None and
                p["close"].get("minute") is not None
            ]
        except Exception as e:
            # 예외 발생 시 해당 요일은 정보 없음으로 처리
            result.append(f"{DAYS[d]} 정보 없음")
            all_breaks.append([])
            continue
        
        # day 값이 없으면 휴무일
        if not day_periods:
            result.append(f"{DAYS[d]} 휴무일")
            continue

        # 시간을 분 단위로 변환하여 전체 시간 계산
        intervals = []
        for p in day_periods:
            start_mins = p["open"]["hour"] * 60 + p["open"]["minute"]
            end_mins = p["close"]["hour"] * 60 + p["close"]["minute"]
            if end_mins == 0:  # 자정은 24*60으로 변환
                end_mins = 24 * 60
            intervals.append((start_mins, end_mins))
        
        # 정렬 후 전체 시간 범위 찾기
        intervals.sort()
        first_start = intervals[0][0]
        last_end = intervals[-1][1]
        
        # 전체 시간 포맷팅
        start_h, start_m = divmod(first_start, 60)
        end_h, end_m = divmod(last_end, 60)
        full_time = f"{format_time(start_h, start_m)}-{format_time(end_h, end_m)}"
        
        # 브레이크타임 계산
        day_breaks = []
        if len(intervals) > 1:
            for i in range(len(intervals) - 1):
                end_time = intervals[i][1]
                next_start = intervals[i + 1][0]
                gap = next_start - end_time
                
                if 0 < gap <= 180:  # 3시간 이하만 브레이크타임으로 간주
                    end_h, end_m = divmod(end_time, 60)
                    next_h, next_m = divmod(next_start, 60)
                    break_time = f"{format_time(end_h, end_m)}-{format_time(next_h, next_m)}"
                    day_breaks.append(break_time)
        
        all_breaks.append(day_breaks)
        result.append(f"{DAYS[d]} {full_time}")
    
    # 브레이크 타임이 모두 동일한 지 체크
    if all_breaks and all(breaks == all_breaks[0] for breaks in all_breaks if breaks):
        if all_breaks[0]:
            result.append(f"쉬는 시간 매일 {', '.join(all_breaks[0])}")
    else:
        # 브레이크 타임이 다르다면 각 요일별로 추가
        result.append("쉬는 시간")
        for d in range(7):
            if all_breaks[d]:
                result.append(f"{DAYS[d]} {', '.join(all_breaks[d])}")
    
    return result