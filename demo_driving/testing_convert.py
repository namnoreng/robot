def convert_to_android_format(sector, side, subzone):
    if sector == 0:
        return "starting_point"
    else:
        sector_chr = chr(ord('a') + int(sector) - 1)
    
    if side == 'left':
        side_chr = 'L'
    elif side == 'right':
        side_chr = 'R'
    elif side == 'Middle':
        side_chr = 'M'
    
    if subzone == 0:
        subzone_chr = 'M'
    else:
        subzone_chr = chr(ord('a') + int(subzone) - 1)
    return f"{sector_chr}{side_chr}{subzone_chr}"



if __name__ == "__main__":
    print("=== Android Studio 좌표 변환 테스트 ===")
    print()
    
    # 사용자가 설명한 좌표 체계 테스트
    test_cases = [
        # (sector, side, subzone, 예상_결과, 설명)
        (0, None, None, "starting_point", "초기 대기 위치"),
        (1, "Middle", 0, "aMM", "전진 후 멈추고 회전하는 위치"),
        (1, "left", 1, "aLa", "좌회전 후 subzone 1의 위치"),
        (1, "left", 2, "aLb", "좌회전 후 subzone 2의 위치"),
        (1, "right", 1, "aRa", "우회전 후 subzone 1의 위치"),
        (1, "right", 2, "aRb", "우회전 후 subzone 2의 위치"),
        (2, "Middle", 0, "bMM", "섹터 2 회전 위치"),
        (2, "left", 1, "bLa", "섹터 2 왼쪽 subzone 1"),
        (2, "left", 2, "bLb", "섹터 2 왼쪽 subzone 2"),
    ]
    
    print("테스트 결과:")
    print("-" * 60)
    
    all_passed = True
    for i, (sector, side, subzone, expected, description) in enumerate(test_cases, 1):
        if sector == 0:
            # 특별한 경우: starting_point
            result = convert_to_android_format(sector, side, subzone)
        else:
            result = convert_to_android_format(sector, side, subzone)
        
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        
        print(f"{i:2d}. {description}")
        print(f"    입력: sector={sector}, side={side}, subzone={subzone}")
        print(f"    예상: {expected}")
        print(f"    결과: {result} {status}")
        print()
    
    print("=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과! Android Studio 좌표와 일치합니다.")
    else:
        print("⚠️  일부 테스트 실패. 함수 수정이 필요합니다.")
    
    print()
    print("=== 기존 예제 테스트 ===")
    # Example usage
    sector = 1
    side = 'left'
    subzone = 2
    formatted_string = convert_to_android_format(sector, side, subzone)
    print(f"convert_to_android_format({sector}, '{side}', {subzone}) = {formatted_string}")  # Output: "aLb"