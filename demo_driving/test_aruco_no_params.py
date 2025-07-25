import cv2 as cv
import numpy as np

def test_aruco_without_parameters():
    """파라미터 없이 ArUco 테스트"""
    print("=== 파라미터 없는 ArUco 테스트 ===")
    
    try:
        # 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 열기 실패")
            return False
        
        # ArUco 딕셔너리만 생성 (파라미터 없이)
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        print("✅ ArUco 딕셔너리 생성 성공")
        
        # 프레임 읽기
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            cap.release()
            return False
        
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        print("✅ 그레이스케일 변환 성공")
        
        # ArUco 탐지 (파라미터 없이!)
        print("ArUco 탐지 시도 (파라미터 없음)...")
        corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict)
        
        print("✅ ArUco 탐지 성공!")
        print(f"탐지된 마커 수: {len(ids) if ids is not None else 0}")
        
        # 마커 그리기 테스트
        if ids is not None and len(ids) > 0:
            cv.aruco.drawDetectedMarkers(frame, corners, ids)
            print("✅ 마커 그리기 성공!")
        
        # 연속 프레임 테스트
        print("연속 프레임 테스트 (10프레임)...")
        for i in range(10):
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict)
            
            if ids is not None:
                print(f"  프레임 {i+1}: {len(ids)}개 마커")
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            cv.imshow('ArUco No Parameters', frame)
            cv.waitKey(100)
        
        print("✅ 모든 테스트 성공!")
        cap.release()
        cv.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        if 'cap' in locals():
            cap.release()
        return False

def test_aruco_custom_parameters():
    """커스텀 파라미터로 ArUco 테스트"""
    print("\n=== 커스텀 파라미터 ArUco 테스트 ===")
    
    try:
        # 빈 파라미터 객체 생성
        parameters = cv.aruco.DetectorParameters()
        print("✅ 파라미터 객체 생성 성공")
        
        # 안전한 속성만 설정 (접근하지 말고 기본값 사용)
        print("기본 파라미터 사용 (속성 접근 안 함)")
        
        # 카메라와 ArUco 테스트
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            return False
        
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return False
        
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # 파라미터 포함 탐지
        print("파라미터 포함 ArUco 탐지...")
        corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        
        print("✅ 파라미터 포함 탐지 성공!")
        print(f"탐지된 마커 수: {len(ids) if ids is not None else 0}")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ 커스텀 파라미터 실패: {e}")
        if 'cap' in locals():
            cap.release()
        return False

if __name__ == "__main__":
    print("ArUco 파라미터 문제 해결 테스트")
    print("=" * 60)
    
    # 1. 파라미터 없이 테스트
    no_param_success = test_aruco_without_parameters()
    
    # 2. 기본 파라미터로 테스트
    if no_param_success:
        param_success = test_aruco_custom_parameters()
    
    print("\n" + "=" * 60)
    print("최종 결과:")
    
    if no_param_success:
        print("✅ ArUco 파라미터 없이 정상 작동")
        print("   해결책: DetectorParameters() 사용 안 함")
        
        if 'param_success' in locals() and param_success:
            print("✅ 기본 파라미터도 작동")
            print("   해결책: 파라미터 속성 접근 금지")
        else:
            print("❌ 파라미터 사용 시 문제")
            print("   해결책: 파라미터 없이 ArUco 사용")
    else:
        print("❌ ArUco 자체에 문제")
        print("   OpenCV 재빌드 필요")
